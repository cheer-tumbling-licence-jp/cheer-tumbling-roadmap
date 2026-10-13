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

# 「何日取れていなければ知らせるか」。
# 失敗したときは通知が飛ぶが、Mac が寝ていて“そもそも動かなかった”ときは
# これまで無音だった。2026-10-11〜13 の3日間、誰も気づけなかったのがこれ。
STALE_DAYS = 3
STATE_PATH = Path.home() / '.config/cta-backup/state.json'

# Google ドライブ側の控え（二重化）。
# Mac 本体が壊れるとローカルの backups/ ごと失われるため。
# ※ 削除は必ずこの「アプリDB」フォルダの中だけに限定する。
#    一つ上の CTA_重要書類_バックアップ 直下には
#    github-recovery-codes_….txt など触ってはいけないものがある。
# 環境変数 CTA_BACKUP_MIRROR で差し替え可（検証用）。
MIRROR_DIR = Path(os.environ.get('CTA_BACKUP_MIRROR') or (
    Path.home() / 'Library/CloudStorage/GoogleDrive-cheernicpro@gmail.com'
    / 'マイドライブ/CTA_重要書類_バックアップ/アプリDB'))


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


def send_mail(subject, lines):
    """通知メールを送る。
    ここで例外を投げると報告そのものが消えるので、必ず握りつぶす。
    送れたかどうかを戻り値で返す（検証で使う）。"""
    conf = load_mail_config()
    if not conf:
        print('（通知メールの設定が無いため送信をスキップ）', file=sys.stderr)
        return False
    try:
        import smtplib
        from email.message import EmailMessage

        msg = EmailMessage()
        msg['From'] = f"チアタンブリング バックアップ <{conf['NOTIFY_EMAIL_USER']}>"
        msg['To'] = conf.get('NOTIFY_EMAIL_TO', conf['NOTIFY_EMAIL_USER'])
        msg['Subject'] = subject
        msg.set_content('\n'.join(lines))

        with smtplib.SMTP_SSL('smtp.gmail.com', 465, timeout=30) as s:
            s.login(conf['NOTIFY_EMAIL_USER'], conf['NOTIFY_EMAIL_PASS'])
            s.send_message(msg)
        print(f'通知メールを送りました：{subject}', file=sys.stderr)
        return True
    except Exception as e:
        print(f'（通知メールの送信にも失敗: {e}）', file=sys.stderr)
        return False


def notify_failure(reason):
    """バックアップが失敗したことをメールで知らせる。"""
    return send_mail(
        '【要対応】Firestore の自動バックアップが失敗しました',
        [
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
        ])


# ─────────────────────────────────────────────
# 「取れていない」ことの見張り
# ─────────────────────────────────────────────
def backup_dates():
    """backups/ 配下にある、中身の入ったバックアップの日付を新しい順に返す。"""
    out = []
    if not BACKUP_DIR.is_dir():
        return out
    for entry in BACKUP_DIR.iterdir():
        if entry.is_symlink() or not entry.is_dir():
            continue
        try:
            dt = datetime.strptime(entry.name, '%Y-%m-%d')
        except ValueError:
            continue
        if any(entry.glob('*.json')):
            out.append(dt)
    return sorted(out, reverse=True)


def load_state():
    try:
        return json.loads(STATE_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}


def save_state(state):
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False), encoding='utf-8')
    except Exception as e:
        print(f'（状態の保存に失敗: {e}）', file=sys.stderr)


def check_staleness(stale_days=STALE_DAYS):
    """一定日数バックアップが取れていなければ知らせる。

    失敗したときは notify_failure が飛ぶが、Mac がスリープ等で
    "そもそも動かなかった" ときは何も飛ばず、気づけなかった。
    その穴を埋めるための見張り。
    毎日同じ通知が届かないよう、送るのは1日1通までにする。
    """
    dates = backup_dates()
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    if dates:
        gap = (today - dates[0]).days
        last_label = dates[0].strftime('%Y-%m-%d')
    else:
        gap = None
        last_label = '（1件も無し）'

    if gap is not None and gap < stale_days:
        return False

    state = load_state()
    today_label = today.strftime('%Y-%m-%d')
    if state.get('stale_notified_on') == today_label:
        print(f'（{stale_days}日以上取れていないが、本日分は通知済みのため省略）', file=sys.stderr)
        return False

    gap_label = f'{gap} 日間' if gap is not None else '一度も'
    sent = send_mail(
        '【要確認】Firestore のバックアップが取れていません',
        [
            f'アプリのデータのバックアップが {gap_label} 取れていません。',
            '',
            f'最後に取れた日： {last_label}',
            f'今日　　　　　： {today_label}',
            '',
            'エラーで失敗したのではなく、処理そのものが動いていない可能性があります。',
            '（毎日 3:00 に実行する設定です。その時刻に Mac がスリープや電源オフだと動きません）',
            '',
            'このまま放置すると、万一データが消えたときに戻せる地点が古いままになります。',
            '',
            '── 確認のしかた ──',
            f'保存先　： {BACKUP_DIR}',
            '詳しい記録： scripts/backup_firestore.err',
            '',
            '手動で動かす場合：',
            '  cd ~/cheer_tumbling_app && python3 scripts/backup_firestore.py',
        ])
    if sent:
        state['stale_notified_on'] = today_label
        save_state(state)
    return sent


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


def node_bindirs(firebase_path):
    """node の実行ファイルが実在する bin ディレクトリを、優先順に返す。

    ※ Path.resolve() を使ってはいけない。
       firebase はシンボリックリンクで、辿ると firebase-tools のライブラリ側
       （…/lib/node_modules/firebase-tools/lib/bin）に行き着く。
       そこに node は無いので、PATH に足しても 127 のままになる。
       （2026-10-13、まさにこれで3日間バックアップが失敗していた）
    """
    cands = []
    # 1) firebase コマンドと同じ bin（リンクは辿らない）。ここに node が同居している
    cands.append(Path(firebase_path).parent)
    # 2) リンク先の実体から親を遡って bin を探す（配置が変わった場合の保険）
    for parent in Path(firebase_path).resolve().parents:
        cands.append(parent / 'bin')
    # 3) nvm 配下の全バージョン（新しい順）。バージョン番号は書かない
    cands += [Path(x) for x in sorted(
        glob.glob(str(Path.home() / '.nvm/versions/node/*/bin')), reverse=True)]
    # 4) システム側
    cands += [Path('/opt/homebrew/bin'), Path('/usr/local/bin'), Path('/usr/bin')]

    out, seen = [], set()
    for d in cands:
        sd = str(d)
        if sd not in seen and (d / 'node').exists():
            seen.add(sd)
            out.append(sd)
    return out


def firebase_env(firebase_path):
    """firebase を動かすための環境変数を作る。

    firebase は #!/usr/bin/env node のシェバンを持つ Node スクリプトなので、
    PATH に node が無いと firebase 本体ではなく node の解決に失敗して exit 127 になる。
    launchd は PATH をほぼ空で起動するため、ここで必ず補う。
    バージョン番号は書かず、node が実在するディレクトリだけを前に足す。
    """
    env = os.environ.copy()
    base = env.get('PATH') or '/usr/local/bin:/usr/bin:/bin'
    have = base.split(os.pathsep)
    add = [d for d in node_bindirs(firebase_path) if d not in have]
    if add:
        env['PATH'] = os.pathsep.join(add) + os.pathsep + base
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


def cleanup_old_backups(keep_days=KEEP_DAYS, base=None):
    """keep_days より古いバックアップフォルダを削除する。

    base を指定すればドライブ側にも同じ条件で効かせられる。
    消すのは base の直下にある YYYY-MM-DD 形式のフォルダだけ。
    想定外のパスを消さないよう、下の条件を全部満たすものに限る：
      ・シンボリックリンクでない（リンクを辿って外を消さないため）
      ・backups/ の直下にある（親が BACKUP_DIR 本体）
      ・名前が YYYY-MM-DD として解釈できる
      ・中身が *.json だけ（別物を置いていた場合に消さない）
    """
    root = Path(base) if base else BACKUP_DIR
    cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) \
        - timedelta(days=keep_days)
    removed, skipped = [], []
    if not root.is_dir():
        return removed
    base = root.resolve()
    for entry in sorted(root.iterdir()):
        if entry.is_symlink() or not entry.is_dir():
            continue
        if entry.parent.resolve() != base:
            continue
        try:
            dt = datetime.strptime(entry.name, '%Y-%m-%d')
        except ValueError:
            continue
        if dt >= cutoff:
            continue
        stray = [f.name for f in entry.iterdir() if f.suffix != '.json']
        if stray:
            skipped.append(f'{entry.name}（{", ".join(stray[:3])} があるため）')
            continue
        shutil.rmtree(entry)
        removed.append(entry.name)
    for sk in skipped:
        print(f'   削除を見送り：{sk}')
    return removed


def mirror_to_drive(day_dir):
    """その日のバックアップを Google ドライブにも置く（二重化の控え）。

    Mac 本体が壊れるとローカルの backups/ ごと失われるため。
    ドライブが未マウント／オフラインでも、ローカルの取得は成功扱いのままにする。
    ここで例外を外に出すと、ドライブの都合でバックアップ自体が失敗してしまう。
    """
    parent = MIRROR_DIR.parent
    if not parent.is_dir():
        print(f'   ドライブに置けませんでした：{parent} が見当たりません'
              f'（未マウントかオフライン）。ローカルの取得は成功しています。')
        return False
    try:
        MIRROR_DIR.mkdir(parents=True, exist_ok=True)
        # 書きかけが本物として残らないよう、一時名で全部コピーしてから差し替える
        dest = MIRROR_DIR / day_dir.name
        tmp = MIRROR_DIR / (day_dir.name + '.copying')
        if tmp.exists():
            shutil.rmtree(tmp)
        shutil.copytree(day_dir, tmp)
        if dest.exists():
            shutil.rmtree(dest)
        tmp.rename(dest)
        n = len(list(dest.glob('*.json')))
        size = sum(f.stat().st_size for f in dest.glob('*.json'))
        print(f'   ドライブにも保存：{dest}（{n}ファイル / {size/1024/1024:.1f}MB）')
        return True
    except Exception as e:
        print(f'   ドライブに置けませんでした（{e}）。ローカルの取得は成功しています。')
        return False


def main(argv=()):
    force = '--force' in argv
    stale_days = STALE_DAYS
    if '--stale-days' in argv:
        stale_days = int(argv[argv.index('--stale-days') + 1])

    BACKUP_DIR.mkdir(exist_ok=True)

    # 取れていない期間が空いていないかを、取得より先に見張る。
    # ここを後ろに置くと、取得に失敗したときに見張りごと飛んでしまう。
    check_staleness(stale_days)

    today = datetime.now().strftime('%Y-%m-%d')
    target_dir = BACKUP_DIR / today

    # Mac の起動時にも動かすようにしたので、同じ日に何度も取りに行かないよう止める。
    if not force and target_dir.is_dir() and any(target_dir.glob('*.json')):
        print(f'本日分（{today}）は取得済みのため省略します。'
              f'　取り直す場合は --force を付けてください。')
        # 取得した時にドライブがオフラインだった場合の取りこぼしを、ここで拾う
        if not (MIRROR_DIR / today).is_dir() and MIRROR_DIR.parent.is_dir():
            print('   ドライブ側に本日分が無いため、控えだけ置きます。')
            if mirror_to_drive(target_dir):
                cleanup_old_backups(KEEP_DAYS, MIRROR_DIR)
        return

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
    if mirror_to_drive(target_dir):
        removed_m = cleanup_old_backups(KEEP_DAYS, MIRROR_DIR)
        if removed_m:
            print(f'   ドライブ側も{KEEP_DAYS}日超を削除：{len(removed_m)}件'
                  f'（{", ".join(removed_m)}）')

    # ここから下が「本当に終わった」ときだけ出るログ
    detail = ' / '.join(f'{k} {v}件' for k, v in counts.items())
    print(f'✅ 完了：{len(COLLECTIONS)} コレクション / {total} ドキュメント'
          f'  → {target_dir}')
    print(f'   内訳：{detail}')
    if removed:
        print(f'   {KEEP_DAYS}日超のため削除：{len(removed)}件'
              f'（{", ".join(removed)}）')


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except Exception as e:
        print(f'❌ エラー: {e}', file=sys.stderr)
        notify_failure(str(e))
        sys.exit(1)
