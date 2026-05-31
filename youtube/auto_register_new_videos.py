#!/usr/bin/env python3
"""
Drive 上にあって manifest 未登録の動画を、自動的に video_manifest.py の
末尾エリアに「未分類（要監督確認）」として追加する。

launchd の毎朝の自動アップロード前に走らせることで、
監督が Drive に動画を置くだけで YouTube アップロードまで自動で進む。

タイトルはファイル名から拡張子を取り除いたもの。
本文は雛形（ファイル名のみ）。監督が後で正式な本文を書ける状態にする。
カテゴリは "skill"（暫定）。
"""

from __future__ import annotations
import re
import sys
import unicodedata
from pathlib import Path

# video_manifest.py から VIDEO_DIR を借用するため import
SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
import video_manifest  # noqa: E402

VIDEO_DIR = Path(video_manifest.DRIVE_DIR)
MANIFEST_PY = SCRIPT_DIR / "video_manifest.py"
IGNORE_FILE = SCRIPT_DIR / ".auto_register_ignore"


def load_ignore_list() -> set[str]:
    if not IGNORE_FILE.exists():
        return set()
    out = set()
    for line in IGNORE_FILE.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.add(_nfc(s))
    return out


def _nfc(s: str) -> str:
    """macOS の NFD ↔ Python の NFC 不一致を解消するため、すべて NFC に揃える。"""
    return unicodedata.normalize("NFC", s)


# 既登録ファイル名集合（NFC 正規化）
EXISTING_FILES = {_nfc(v["file"]) for v in video_manifest.VIDEOS}


def list_drive_videos() -> list[str]:
    if not VIDEO_DIR.exists():
        return []
    # .mov / .mp4 / .MOV / .MP4 を NFC 正規化して返す
    return sorted([_nfc(p.name) for p in VIDEO_DIR.iterdir() if p.suffix.lower() in (".mov", ".mp4")])


def find_unregistered() -> list[str]:
    drive_files = list_drive_videos()
    ignored = load_ignore_list()
    return [f for f in drive_files if f not in EXISTING_FILES and f not in ignored]


def title_from_filename(filename: str) -> str:
    """ファイル名からタイトルを推測する。拡張子を除き、IMG_xxxx.mov 接頭辞があれば除去。"""
    stem = Path(filename).stem
    # IMG_xxxx.mov<本来の名前> という旧形式を取り除く
    stem = re.sub(r"^IMG_\d+\.mov", "", stem)
    return stem


def make_entry_block(filename: str) -> str:
    title = title_from_filename(filename)
    body = (
        f"{title} の解説動画です。\n\n"
        f"※ この本文は auto_register_new_videos.py が自動生成した雛形です。\n"
        f"監督確認後、適切な解説・意識ポイント・関連技に書き換えてください。\n"
    )
    return (
        "    {\n"
        f'        "file": "{filename}",\n'
        f'        "title": "{title}",\n'
        '        "body": """' + body + '""",\n'
        f'        "tags": ["{title}", "未分類"],\n'
        '        "category": "skill",\n'
        '        "_auto_registered": True,  # auto_register_new_videos.py により追加。監督確認後に削除\n'
        "    },\n"
    )


def append_entries(new_files: list[str]) -> None:
    if not new_files:
        return

    text = MANIFEST_PY.read_text(encoding="utf-8")

    # VIDEOS リストの閉じ "] " の位置を見つける
    # 末尾の "VIDEOS = [\n...\n]" の閉じ ] の直前に挿入
    match = re.search(r"\n\]\s*\n", text)
    if not match:
        # フォールバック：ファイル末尾に追加されているとは限らない
        # VIDEOS リストの末尾を別パターンで探す
        # ] が単独で行に出る最後を探す
        lines = text.split("\n")
        last_bracket = None
        for i, line in enumerate(lines):
            if line.strip() == "]":
                last_bracket = i
        if last_bracket is None:
            raise RuntimeError("VIDEOS リストの閉じ ] が見つかりません")
        insert_block = (
            "\n    # ===================== 自動登録（要監督確認） ===================== \n"
            + "".join(make_entry_block(f) for f in new_files)
        )
        lines.insert(last_bracket, insert_block)
        new_text = "\n".join(lines)
    else:
        insert_pos = match.start()
        insert_block = (
            "\n    # ===================== 自動登録（要監督確認） ===================== \n"
            + "".join(make_entry_block(f) for f in new_files)
        )
        new_text = text[:insert_pos] + "\n" + insert_block + text[insert_pos:]

    MANIFEST_PY.write_text(new_text, encoding="utf-8")
    print(f"✅ video_manifest.py に {len(new_files)} 件を自動登録しました")
    for f in new_files:
        print(f"  - {f} -> title: {title_from_filename(f)}")


def main() -> None:
    new_files = find_unregistered()
    if not new_files:
        print("✅ 未登録動画はありません。")
        return
    print(f"🆕 未登録動画 {len(new_files)} 件を検出:")
    for f in new_files:
        print(f"  - {f}")

    if "--dry-run" in sys.argv:
        print("\n（dry-run: 何も書き込みません）")
        return

    append_entries(new_files)

    # video_manifest.json も再生成
    print("\n🔄 video_manifest.json を再生成...")
    import subprocess
    subprocess.run([sys.executable, str(SCRIPT_DIR / "video_manifest.py")], check=True)


if __name__ == "__main__":
    main()
