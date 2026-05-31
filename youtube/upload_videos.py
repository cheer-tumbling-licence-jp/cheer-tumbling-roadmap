#!/usr/bin/env python3
"""
YouTube 一括アップロードスクリプト

使い方:
  1. 初回のみ: client_secrets.json をこのフォルダに置く（Google Cloud Console から取得）
  2. python3 upload_videos.py            # 全件アップロード（既にアップ済みはスキップ）
  3. python3 upload_videos.py --dry-run  # ファイル確認のみ、アップロードしない
  4. python3 upload_videos.py --only "ホロー"  # タイトルに「ホロー」を含むものだけ

要件:
  pip3 install google-auth google-auth-oauthlib google-api-python-client
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError
except ImportError:
    print("❌ 必要なライブラリが入っていません。以下を実行してください：")
    print("   pip3 install google-auth google-auth-oauthlib google-api-python-client")
    sys.exit(1)

HERE = Path(__file__).parent
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CLIENT_SECRETS = HERE / "client_secrets.json"
TOKEN_FILE = HERE / "token.json"
MANIFEST_FILE = HERE / "video_manifest.json"
UPLOAD_LOG = HERE / "uploaded.json"  # アップ済み記録


def get_authenticated_service():
    """OAuth 認証 → YouTube API クライアント取得"""
    if not CLIENT_SECRETS.exists():
        print(f"❌ {CLIENT_SECRETS} がありません。")
        print("   Google Cloud Console から OAuth クライアント（デスクトップアプリ）を作成し、")
        print(f"   ダウンロードした JSON を {CLIENT_SECRETS} に置いてください。")
        sys.exit(1)

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRETS), SCOPES)
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
        print(f"✅ 認証完了。トークンを {TOKEN_FILE.name} に保存しました。")

    return build("youtube", "v3", credentials=creds)


def load_manifest():
    if not MANIFEST_FILE.exists():
        print(f"❌ {MANIFEST_FILE} がありません。先に video_manifest.py を実行してください。")
        sys.exit(1)
    return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))


def load_uploaded():
    if UPLOAD_LOG.exists():
        return json.loads(UPLOAD_LOG.read_text(encoding="utf-8"))
    return {}


def save_uploaded(log):
    UPLOAD_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def _stage_locally(src_path: str) -> str:
    """Drive ストリーミング上のファイルはタイムアウトを起こしやすいため、
    一度 /tmp にコピーしてからアップロードに渡す。コピー成功時は
    一時パスを返す。コピー失敗時は元パスを返す（フォールバック）。"""
    import shutil
    import tempfile
    src = Path(src_path)
    if not src.exists():
        return src_path
    try:
        # 拡張子は .mov / .MOV など元に揃える
        tmp = Path(tempfile.gettempdir()) / f"yt_upload_{os.getpid()}_{src.name}"
        if tmp.exists():
            tmp.unlink()
        # Drive ストリーミングからローカル /tmp に読み出してコピー
        shutil.copy(str(src), str(tmp))
        return str(tmp)
    except Exception as e:
        print(f"  ⚠️ ローカルステージング失敗（{e}）、Drive 直接読み出しにフォールバック")
        return src_path


def upload_one(youtube, item):
    """1本アップロードして video_id を返す"""
    body = {
        "snippet": {
            "title": item["title"],
            "description": item["description"],
            "tags": item["tags"],
            "categoryId": item["category_id"],
            "defaultLanguage": item["language"],
            "defaultAudioLanguage": item["default_audio_language"],
        },
        "status": {
            "privacyStatus": item["privacy_status"],
            "selfDeclaredMadeForKids": item["made_for_kids"],
        },
    }
    # Drive ストリーミングタイムアウト対策：先にローカル /tmp にステージング
    staged_path = _stage_locally(item["file_path"])
    staged_is_tmp = staged_path != item["file_path"]
    try:
        media = MediaFileUpload(staged_path, chunksize=-1, resumable=True)
        request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

        response = None
        while response is None:
            try:
                status, response = request.next_chunk()
            except HttpError as e:
                if e.resp.status in (500, 502, 503, 504):
                    print(f"  ⚠️ 一時エラー {e.resp.status}、5秒後リトライ")
                    time.sleep(5)
                    continue
                raise
        return response["id"]
    finally:
        # 一時コピーを削除
        if staged_is_tmp:
            try:
                Path(staged_path).unlink()
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", type=str, default=None, help="タイトル絞り込み（部分一致）")
    parser.add_argument("--limit", type=int, default=None, help="この回でアップロードする最大本数")
    args = parser.parse_args()

    items = load_manifest()
    if args.only:
        items = [it for it in items if args.only in it["title"]]
        print(f"絞り込み: {len(items)} 件")

    if args.dry_run:
        print("=== DRY RUN ===")
        for it in items:
            print(f"  - {it['title']} ({it['file_size_mb']} MB)")
        return

    uploaded = load_uploaded()
    youtube = get_authenticated_service()
    print(f"📤 アップロード開始: {len(items)} 件")

    uploaded_this_run = 0
    for i, item in enumerate(items, 1):
        key = Path(item["file_path"]).name
        if key in uploaded:
            print(f"[{i}/{len(items)}] スキップ（既出）: {item['title']}")
            continue

        if args.limit is not None and uploaded_this_run >= args.limit:
            print(f"📊 この回の上限 ({args.limit}本) に到達、ここで停止")
            break

        print(f"[{i}/{len(items)}] {item['title']} ({item['file_size_mb']} MB)")
        try:
            video_id = upload_one(youtube, item)
            url = f"https://youtu.be/{video_id}"
            uploaded[key] = {"id": video_id, "url": url, "title": item["title"]}
            save_uploaded(uploaded)
            uploaded_this_run += 1
            print(f"  ✅ {url}")
        except Exception as e:
            msg = str(e)
            print(f"  ❌ 失敗: {e}")
            # ファイルアクセスエラー（Drive ストリーミングのキャッシュ一時問題等）はスキップして次の動画へ
            if (isinstance(e, OSError)
                    or 'Operation not permitted' in msg
                    or 'Errno' in msg
                    or 'No such file' in msg):
                print("  ⚠️ ファイルアクセスエラー。この動画はスキップして次へ進みます。")
                continue
            # API クォータ／レート超過、認証エラーは停止
            if 'quotaExceeded' in msg or 'rate' in msg.lower() or 'invalid_grant' in msg or 'unauthorized' in msg.lower():
                print("  ⚠️ クォータ/認証エラー。本日は停止します。")
                break
            # その他の未知エラーも次の動画へ進む（過去の "break で全停止" を避ける）
            print("  ⚠️ 未知エラー。この動画はスキップして次へ進みます。")
            continue

    print(f"\n🎉 完了。アップ済み: {len(uploaded)} 件")
    print(f"   結果ログ: {UPLOAD_LOG}")


if __name__ == "__main__":
    main()
