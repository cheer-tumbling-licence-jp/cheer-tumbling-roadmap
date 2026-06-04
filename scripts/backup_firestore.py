#!/usr/bin/env python3
"""
Firestore データを日次スナップショットとして保存する。

仕組み：
- firebase CLI のアクセストークン（~/.config/configstore/firebase-tools.json）を利用
- 主要コレクション（users, assignments, submissions, bug_reports）を REST API で取得
- backups/{YYYY-MM-DD}/{collection}.json として保存
- 30日より古いバックアップは自動削除

実行方法：
    python3 scripts/backup_firestore.py

launchd ジョブ例（毎日 03:00）：
    ~/Library/LaunchAgents/com.cheertumbling.firestorebackup.plist
"""
import json
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

CREDS_PATH = Path.home() / '.config/configstore/firebase-tools.json'


def get_token():
    """firebase CLI のキャッシュからアクセストークンを取得。期限切れなら更新。"""
    if not CREDS_PATH.exists():
        raise RuntimeError(f'Firebase CLI credentials not found at {CREDS_PATH}. Run `firebase login` first.')
    creds = json.loads(CREDS_PATH.read_text())
    tokens = creds.get('tokens', {})
    token = tokens.get('access_token')
    expires_at = tokens.get('expires_at', 0)

    if not token or expires_at < int(time.time() * 1000) + 60_000:
        # トークン更新のため firebase コマンドを軽く叩く
        import subprocess
        subprocess.run(['firebase', 'projects:list'], capture_output=True, check=True)
        creds = json.loads(CREDS_PATH.read_text())
        token = creds['tokens']['access_token']
    return token


def fetch_collection(name, token):
    """Firestore REST API で1コレクションを全件取得。"""
    docs = []
    page_token = None
    while True:
        url = f'https://firestore.googleapis.com/v1/projects/{PROJECT_ID}/databases/(default)/documents/{name}?pageSize=300'
        if page_token:
            url += f'&pageToken={page_token}'
        req = urllib.request.Request(url, headers={'Authorization': f'Bearer {token}'})
        try:
            with urllib.request.urlopen(req) as resp:
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
    for entry in BACKUP_DIR.iterdir():
        if not entry.is_dir():
            continue
        try:
            dt = datetime.strptime(entry.name, '%Y-%m-%d')
            if dt < cutoff:
                import shutil
                shutil.rmtree(entry)
                print(f'  🗑️  古いバックアップ削除: {entry.name}')
        except ValueError:
            continue


def main():
    BACKUP_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime('%Y-%m-%d')
    target_dir = BACKUP_DIR / today
    target_dir.mkdir(exist_ok=True)

    print(f'📦 Firestore backup → {target_dir}')
    token = get_token()

    total = 0
    for col in COLLECTIONS:
        docs = fetch_collection(col, token)
        out = {
            'collection': col,
            'fetched_at': datetime.now().isoformat(),
            'count': len(docs),
            'documents': docs
        }
        (target_dir / f'{col}.json').write_text(
            json.dumps(out, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )
        print(f'  ✅ {col:20s} {len(docs):4d} 件')
        total += len(docs)

    print(f'\n合計 {total} 件 保存完了')

    cleanup_old_backups()
    print('完了 ✨')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ エラー: {e}', file=sys.stderr)
        sys.exit(1)
