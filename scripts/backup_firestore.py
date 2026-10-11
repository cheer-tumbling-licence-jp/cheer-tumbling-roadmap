#!/usr/bin/env python3
"""
Firestore データを日次スナップショットとして保存する。

仕組み：
- firebase CLI のアクセストークン（~/.config/configstore/firebase-tools.json）を利用
- 主要コレクション（users, assignments, submissions, bug_reports）を REST API で取得
- backups/{YYYY-MM-DD}/{collection}.json として保存
- 30日より古いバックアップは自動削除
- 失敗したら協会アドレスへメールで知らせる

実行方法：
    python3 scripts/backup_firestore.py

launchd ジョブ（毎日 03:00）：
    ~/Library/LaunchAgents/com.cheertumbling.firestorebackup.plist

失敗通知に使う資格情報（リポジトリ外・600）：
    ~/.config/cta-backup/mail.env
        NOTIFY_EMAIL_USER=...（Gmail アドレス）
        NOTIFY_EMAIL_PASS=...（Gmail アプリパスワード）
        NOTIFY_EMAIL_TO=cheer.tumbling.association@gmail.com
    値は Firebase Secret Manager と同じもの：
        firebase functions:secrets:access NOTIFY_EMAIL_USER
        firebase functions:secrets:access NOTIFY_EMAIL_PASS

──────────────────────────────────────────────────────────────
2026-10-11 の修正（3か月バックアップが0件だった原因）
──────────────────────────────────────────────────────────────
firebase CLI は #!/usr/bin/env node のシェバンを持つ Node スクリプト。
launchd は PATH をほぼ空で起動するため node が解決できず、
firebase ではなく node の不在で exit 127 になっていた。
対話シェルでは nvm が PATH に入っているので気づけなかった。
→ firebase と同じ bin ディレクトリを PATH の先頭に足して解決する。
   nvm のバージョン番号はハードコードしない（将来変わるため）。

同時に、成功していないのに成功に見えるログも直した。
以前は処理の「開始時」に「📦 Firestore backup → …」と出していたため、
その直後に落ちてもログ上は毎日動いているように見えていた。
"""
import glob
import json
import os
import shutil
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timedelta
import sys
import time

PROJECT_ID = 'cheer-tumbling-roadmap'
COLLECTIONS = ['users', 'assignments', 'submissions', 'bug_reports']
BACKUP_DIR = Path(__file__).parent.parent / 'backups'
KEEP_DAYS = 30

# ここが空だと「取れていない」とみなして失敗扱いにする。
# 取得はできたが中身が空、という静かな失敗を見逃さないため。
MUST_NOT_BE_EMPTY = 'users'

CREDS_PATH = Path.home() / '.config/configstore/firebase-tools.json'
MAIL_ENV_PATH = Path.home() / '.config/cta-backup/mail.env'


# ─────────────────────────────────────────────
# 失敗通知
# ─────────────────────────────────────────────
def load_mail_config():
    """失敗通知用の設定を読む。無ければ None（通知なしで続行）。"""
    if not MAIL_ENV_PATH.exists():
        return None
    conf = {}
    for line in MAIL_ENV_PATH.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        k, v = line.split('=', 1)
        conf[k.strip()] = v.strip()
    if not conf.get('NOTIFY_EMAIL_USER') or not conf.get('NOTIFY_EMAIL_PASS'):
        return None
    return conf


def notify_failure(reason):
    """バックアップが失敗したことをメールで知らせる。
    ここで例外を投げると失敗の報告自体が消えるので、必ず握りつぶす。"""
    conf = load_mail_config()
    if not conf:
        print('（通知メールの設定が無いため送信をスキップ）', file=sys.stderr)
        return
    try:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg['From'] = f"チアタンブリング バックアップ <{conf['NOTIFY_EMAIL_USER']}>"
        msg['To'] = conf.get('NOTIFY_EMAIL_TO', conf['NOTIFY_EMAIL_USER'])
        msg['Subject'] = '【要対応】Firestore の自動バックアップが失敗しました'
        msg.set_content('\n'.join([
            'アプリのデータの自動バックアップが失敗しました。',
            '',
            f'日時　： {datetime.now().strftime("%Y-%m-%d %H:%M")}',
            f'内容　： {reason}',
            '',
            'このまま放置すると、万一データが消えたときに戻せません。',
            '',
            '── 確認のしかた ──',
            f'保存先　： {BACKUP_DIR}',
            '詳しい記録： scripts/backup_firestore.err',
            '',
            '手動で動かす場合：',
            '  cd ~/cheer_tumbling_app && python3 scripts/backup_firestore.py',
        ]))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as s:
            s.login(conf['NOTIFY_EMAIL_USER'], conf['NOTIFY_EMAIL_PASS'])
            s.send_message(msg)
        print('失敗を通知メールで送りました', file=sys.stderr)
    except Exception as e:
        print(f'（通知メールの送信にも失敗: {e}）', file=sys.stderr)


# ─────────────────────────────────────────────
# firebase CLI
# ─────────────────────────────────────────────
def find_firebase_cli():
    """firebase 実行ファイルを探索。PATH → nvm 配下の順で当たる最初のものを返す。
    nvm 配下は、同じ bin に node がある版を優先する（無いと実行できないため）。"""
    exe = shutil.which('firebase')
    if exe:
        return exe
    candidates = sorted(
        glob.glob(str(Path.home() / '.nvm/versions/node/*/bin/firebase')),
        reverse=True
    )
    with_node = [c for c in candidates if (Path(c).parent / 'node').exists()]
    if with_node:
        return with_node[0]
    if candidates:
        return candidates[0]
    raise RuntimeError(
        'firebase CLI が見つかりません。`npm i -g firebase-tools` を実行するか nvm を確認してください。'
    )


def firebase_env(firebase_path):
    """firebase を動かすための環境変数を作る。

    firebase は #!/usr/bin/env node のシェバンを持つ Node スクリプトなので、
    PATH に node が無いと firebase 本体ではなく node の解決に失敗して exit 127 になる。
    launchd は PATH をほぼ空で起動するため、ここで必ず補う。
    バージョン番号は書かず、見つけた firebase と同じ bin ディレクトリを使う。
    """
    env = os.environ.copy()
    bindir = str(Path(firebase_path).resolve().parent)
    base = env.get('PATH') or '/usr/local/bin:/usr/bin:/bin'
    if bindir not in base.split(os.pathsep):
        env['PATH'] = bindir + os.pathsep + base
    return env


def get_token():
    """firebase CLI のキャッシュからアクセストークンを取得。期限切れなら更新。"""
    if not CREDS_PATH.exists():
        raise RuntimeError(
            f'firebase CLI の資格情報がありません（{CREDS_PATH}）。`firebase login` を実行してください。'
        )
    creds = json.loads(CREDS_PATH.read_text())
    tokens = creds.get('tokens', {})
    token = tokens.get('access_token')
    expires_at = tokens.get('expires_at', 0)

    if not token or expires_at < int(time.time() * 1000) + 60_000:
        fb = find_firebase_cli()
        r = subprocess.run(
            [fb, 'projects:list'],
            capture_output=True, text=True, env=firebase_env(fb)
        )
        if r.returncode != 0:
            raise RuntimeError(
                f'トークンの更新に失敗しました（{fb} projects:list → 終了コード {r.returncode}）。\n'
                f'  stderr: {(r.stderr or "").strip()[:500]}'
            )
        creds = json.loads(CREDS_PATH.read_text())
        token = creds.get('tokens', {}).get('access_token')
        if not token:
            raise RuntimeError('トークンを更新しましたが access_token を取得できませんでした。')
    return token


# ─────────────────────────────────────────────
# 取得と保存
# ─────────────────────────────────────────────
def fetch_collection(name, token):
    """Firestore REST API で1コレクションを全件取得。"""
    docs = []
    page_token = None
    while True:
        url = (f'https://firestore.googleapis.com/v1/projects/{PROJECT_ID}'
               f'/databases/(default)/documents/{name}?pageSize=300')
        if page_token:
            url += f'&pageToken={page_token}'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return []  # コレクションが存在しない
            raise
        docs.extend(data.get('documents', []))
        page_token = data.get('nextPageToken')
        if not page_token:
            break
    return docs


def cleanup_old_backups():
    """KEEP_DAYS より古いバックアップフォルダを削除。"""
    cutoff = datetime.now() - timedelta(days=KEEP_DAYS)
    removed = []
    for entry in BACKUP_DIR.iterdir():
        if not entry.is_dir():
            continue
        try:
            dt = datetime.strptime(entry.name, '%Y-%m-%d')
        except ValueError:
            continue
        if dt < cutoff:
            shutil.rmtree(entry)
            removed.append(entry.name)
    return removed


def main():
    BACKUP_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    target_dir = BACKUP_DIR / today

    token = get_token()
    target_dir.mkdir(exist_ok=True)

    # 取得 → 書き込み。ここを抜けて初めて「完了」と名乗る。
    counts = {}
    total = 0
    for col in COLLECTIONS:
        docs = fetch_collection(col, token)
        (target_dir / f'{col}.json').write_text(
            json.dumps({
                'collection': col,
                'fetched_at': datetime.now().isoformat(),
                'count': len(docs),
                'documents': docs,
            }, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        counts[col] = len(docs)
        total += len(docs)

    # 空のファイルを並べて「成功」と言わないための歯止め
    if counts.get(MUST_NOT_BE_EMPTY, 0) == 0:
        raise RuntimeError(
            f'{MUST_NOT_BE_EMPTY} が 0 件でした。権限か接続の問題が疑われます（保存先: {target_dir}）'
        )

    removed = cleanup_old_backups()

    # ここから下が「本当に終わった」ときだけ出るログ
    detail = ' / '.join(f'{k} {v}件' for k, v in counts.items())
    print(f'✅ 完了：{len(COLLECTIONS)} コレクション / {total} ドキュメント'
          f'  → {target_dir}')
    print(f'   内訳：{detail}')
    if removed:
        print(f'   30日超のため削除：{", ".join(removed)}')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ エラー: {e}', file=sys.stderr)
        notify_failure(str(e))
        sys.exit(1)
