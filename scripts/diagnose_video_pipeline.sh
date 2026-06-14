#!/bin/bash
# 動画パイプライン総合診断
# ── セッション起動時に「いま動画運用がどの状態か」を一目で見るためのスクリプト ──
#
# チェック項目（上から順に表示）:
#   1. Drive vs manifest 差分（Drive にあって未登録の動画）
#   2. manifest vs Drive 差分（manifest にあって Drive 不在の動画）
#   3. アップロード進捗（uploaded.json vs manifest）
#   4. launchd 健全性（OAuth トークン期限切れ・前回終了ステータス）
#   5. アプリ反映（index.html への youtubeId 反映状況）
#
# 使い方:
#   bash scripts/diagnose_video_pipeline.sh
#
# 終了コード: 即対応事項があれば 1、すべて健全なら 0

cd "$(dirname "$0")/.." || exit 1

# ── 色定義（ANSI escape） ──
RED=$'\033[31m'
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
CYAN=$'\033[36m'
BOLD=$'\033[1m'
DIM=$'\033[2m'
RESET=$'\033[0m'

OK="${GREEN}✅${RESET}"
WARN="${YELLOW}⚠️ ${RESET}"
NG="${RED}❌${RESET}"
INFO="${CYAN}ℹ️ ${RESET}"

DRIVE_DIR="/Users/don/Library/CloudStorage/GoogleDrive-cheernicpro@gmail.com/マイドライブ/アプリ動画 2026"
MANIFEST_JSON="youtube/video_manifest.json"
UPLOADED_JSON="youtube/uploaded.json"
LAUNCHD_ERR="youtube/launchd.err"
LAUNCHD_LOG="youtube/launchd.log"
LAUNCHD_LABEL="com.cheernic.yt-upload"

# 即対応事項を集めるバッファ（最後にまとめて表示）
TODO_FILE=$(mktemp -t diag_pipeline_todo.XXXXXX)
trap 'rm -f "$TODO_FILE"' EXIT

add_todo() { echo "$1" >> "$TODO_FILE"; }

# ── ヘッダ ──
echo "${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo "${BOLD}║  🎬 動画パイプライン総合診断                                 ║${RESET}"
echo "${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo

# ── 前提ファイルチェック ──
missing=0
if [ ! -d "$DRIVE_DIR" ]; then
    echo "${NG} Drive フォルダが見つかりません: $DRIVE_DIR"
    add_todo "Drive がマウントされていません（Google Drive アプリを起動）"
    missing=1
fi
if [ ! -f "$MANIFEST_JSON" ]; then
    echo "${NG} $MANIFEST_JSON が見つかりません。youtube/video_manifest.py を実行してください"
    add_todo "python3 youtube/video_manifest.py を実行して manifest を生成"
    missing=1
fi
if [ ! -f "$UPLOADED_JSON" ]; then
    echo "${NG} $UPLOADED_JSON が見つかりません"
    missing=1
fi
if [ $missing -eq 1 ]; then
    echo
    echo "${RED}前提ファイル不足のため診断を中断します${RESET}"
    exit 1
fi

# ─────────────────────────────────────────────────────────
# 1. Drive vs manifest 差分
# ─────────────────────────────────────────────────────────
echo "${BOLD}── 1. Drive vs manifest 差分（未登録の新規動画）──${RESET}"
DIFF_OUT=$(DRIVE_DIR="$DRIVE_DIR" MANIFEST_JSON="$MANIFEST_JSON" python3 - <<'PY'
import json, os, sys, unicodedata
from pathlib import Path

drive_dir = Path(os.environ['DRIVE_DIR'])
manifest = json.load(open(os.environ['MANIFEST_JSON']))

def nfc(s): return unicodedata.normalize('NFC', s)

# Drive 上の動画拡張子
VIDEO_EXTS = {'.mov', '.mp4', '.m4v', '.MOV', '.MP4', '.M4V'}
drive_files = set()
for p in drive_dir.iterdir():
    if p.is_file() and p.suffix in VIDEO_EXTS and not p.name.startswith('.'):
        drive_files.add(nfc(p.name))

manifest_files = {nfc(Path(m['file_path']).name) for m in manifest}

unregistered = sorted(drive_files - manifest_files)
print(f"COUNT_DRIVE={len(drive_files)}")
print(f"COUNT_MANIFEST={len(manifest_files)}")
print(f"COUNT_UNREG={len(unregistered)}")
for f in unregistered:
    print(f"UNREG::{f}")
PY
)
COUNT_DRIVE=$(echo "$DIFF_OUT" | grep '^COUNT_DRIVE=' | cut -d= -f2)
COUNT_MANIFEST=$(echo "$DIFF_OUT" | grep '^COUNT_MANIFEST=' | cut -d= -f2)
COUNT_UNREG=$(echo "$DIFF_OUT" | grep '^COUNT_UNREG=' | cut -d= -f2)
UNREG_LIST=$(echo "$DIFF_OUT" | grep '^UNREG::' | sed 's/^UNREG:://')

echo "  ${DIM}Drive 上の動画: ${COUNT_DRIVE} 本 / manifest 登録済: ${COUNT_MANIFEST} 本${RESET}"
if [ "$COUNT_UNREG" -eq 0 ]; then
    echo "  ${OK} Drive 上のすべての動画が manifest に登録されています"
else
    echo "  ${WARN} ${YELLOW}未登録の動画が ${COUNT_UNREG} 本あります（manifest 追記が必要）${RESET}"
    echo "$UNREG_LIST" | sed "s/^/      - /"
    add_todo "manifest 未登録の動画 ${COUNT_UNREG} 本を youtube/video_manifest.py の VIDEOS リストに追記"
fi
echo

# ─────────────────────────────────────────────────────────
# 2. manifest vs Drive 差分（リネーム/削除検出）
# ─────────────────────────────────────────────────────────
echo "${BOLD}── 2. manifest vs Drive 差分（Drive から消えた動画）──${RESET}"
MISSING_OUT=$(DRIVE_DIR="$DRIVE_DIR" MANIFEST_JSON="$MANIFEST_JSON" python3 - <<'PY'
import json, os, unicodedata
from pathlib import Path

drive_dir = Path(os.environ['DRIVE_DIR'])
manifest = json.load(open(os.environ['MANIFEST_JSON']))

def nfc(s): return unicodedata.normalize('NFC', s)

VIDEO_EXTS = {'.mov', '.mp4', '.m4v', '.MOV', '.MP4', '.M4V'}
drive_files = set()
for p in drive_dir.iterdir():
    if p.is_file() and p.suffix in VIDEO_EXTS and not p.name.startswith('.'):
        drive_files.add(nfc(p.name))

missing = []
for m in manifest:
    fname = nfc(Path(m['file_path']).name)
    if fname not in drive_files:
        missing.append((fname, m.get('title', '(無題)')))

print(f"COUNT_MISSING={len(missing)}")
for fname, title in sorted(missing):
    print(f"MISSING::{fname}\t{title}")
PY
)
COUNT_MISSING=$(echo "$MISSING_OUT" | grep '^COUNT_MISSING=' | cut -d= -f2)
if [ "$COUNT_MISSING" -eq 0 ]; then
    echo "  ${OK} manifest のすべての動画が Drive 上に存在します"
else
    echo "  ${NG} ${RED}Drive に存在しない動画が ${COUNT_MISSING} 本あります（リネーム/削除？）${RESET}"
    echo "$MISSING_OUT" | grep '^MISSING::' | sed 's/^MISSING:://' | while IFS=$'\t' read -r fname title; do
        echo "      - $fname  ${DIM}(タイトル: $title)${RESET}"
    done
    add_todo "Drive から消えている manifest 登録動画 ${COUNT_MISSING} 本のファイル名整合を確認"
fi
echo

# ─────────────────────────────────────────────────────────
# 3. アップロード進捗
# ─────────────────────────────────────────────────────────
echo "${BOLD}── 3. アップロード進捗 ──${RESET}"
PROG_OUT=$(MANIFEST_JSON="$MANIFEST_JSON" UPLOADED_JSON="$UPLOADED_JSON" python3 - <<'PY'
import json, os, unicodedata
from pathlib import Path

manifest = json.load(open(os.environ['MANIFEST_JSON']))
uploaded = json.load(open(os.environ['UPLOADED_JSON']))

def nfc(s): return unicodedata.normalize('NFC', s)

uploaded_keys = {nfc(k) for k in uploaded.keys()}

pending = []
for m in manifest:
    fname = nfc(Path(m['file_path']).name)
    if fname not in uploaded_keys:
        pending.append((fname, m.get('title', '(無題)').split('｜')[0]))

print(f"TOTAL={len(manifest)}")
print(f"UPLOADED={len(uploaded)}")
print(f"PENDING={len(pending)}")
for fname, title in pending:
    print(f"PENDING::{title}\t{fname}")
PY
)
TOTAL=$(echo "$PROG_OUT" | grep '^TOTAL=' | cut -d= -f2)
UPLOADED=$(echo "$PROG_OUT" | grep '^UPLOADED=' | cut -d= -f2)
PENDING=$(echo "$PROG_OUT" | grep '^PENDING=' | cut -d= -f2)

echo "  ${INFO} アップロード済: ${BOLD}${UPLOADED}${RESET} / ${TOTAL} 本"
if [ "$PENDING" -eq 0 ]; then
    echo "  ${OK} すべての manifest 登録動画がアップロード済みです"
else
    echo "  ${WARN} 残り ${PENDING} 本（launchd の日次 --limit 6 で順次アップロード）"
    echo "$PROG_OUT" | grep '^PENDING::' | sed 's/^PENDING:://' | head -10 | while IFS=$'\t' read -r title fname; do
        echo "      - $title  ${DIM}($fname)${RESET}"
    done
    if [ "$PENDING" -gt 10 ]; then
        echo "      ${DIM}…ほか $((PENDING - 10)) 本${RESET}"
    fi
fi
echo

# ─────────────────────────────────────────────────────────
# 4. launchd 健全性
# ─────────────────────────────────────────────────────────
echo "${BOLD}── 4. launchd 健全性 ──${RESET}"
launchd_ok=1
OAUTH_FAIL=0  # OAuth 失効が検出されたかのフラグ
OAUTH_PATTERN="invalid_grant|expired|revoked|Token has been|RefreshError"

# 4a. launchctl での前回終了ステータス
LCTL_LINE=$(launchctl list 2>/dev/null | grep "$LAUNCHD_LABEL" || true)
LCTL_STATUS=""
if [ -z "$LCTL_LINE" ]; then
    echo "  ${NG} launchd ジョブ '${LAUNCHD_LABEL}' が未登録です"
    add_todo "launchctl で ${LAUNCHD_LABEL} を再ロード（plist が外れている可能性）"
    launchd_ok=0
else
    # 形式: PID  STATUS  LABEL
    LCTL_PID=$(echo "$LCTL_LINE" | awk '{print $1}')
    LCTL_STATUS=$(echo "$LCTL_LINE" | awk '{print $2}')
    if [ "$LCTL_STATUS" = "0" ]; then
        echo "  ${OK} launchd ジョブ登録あり（前回終了ステータス: 0）"
    elif [ "$LCTL_STATUS" = "-" ]; then
        echo "  ${INFO} launchd ジョブ登録あり（未実行 or 実行履歴なし: status=-）"
    else
        echo "  ${NG} ${RED}launchd 前回終了ステータス: ${LCTL_STATUS}（異常終了）${RESET}"
        add_todo "launchd 前回終了ステータス ${LCTL_STATUS} の原因を youtube/launchd.log で確認"
        launchd_ok=0
    fi
fi

# 4b. launchd.err の OAuth トークン期限切れ検出
#     ※ youtube/upload_today.sh が stderr を grep でフィルタしているため
#       launchd.err は空のまま、エラー本体は launchd.log の末尾に流れている
if [ -f "$LAUNCHD_ERR" ]; then
    ERR_SIZE=$(wc -c < "$LAUNCHD_ERR" | tr -d ' ')
    if [ "$ERR_SIZE" -eq 0 ]; then
        echo "  ${OK} launchd.err は空（stderr フィルタを通過したエラーなし）"
    else
        # OAuth 失効パターン
        if tail -50 "$LAUNCHD_ERR" | grep -E "$OAUTH_PATTERN" >/dev/null 2>&1; then
            echo "  ${NG} ${RED}OAuth トークン失効の兆候を launchd.err から検出${RESET}"
            tail -50 "$LAUNCHD_ERR" | grep -E "$OAUTH_PATTERN" | tail -3 | sed 's/^/      /'
            OAUTH_FAIL=1
            launchd_ok=0
        else
            echo "  ${WARN} launchd.err にエラー出力あり（${ERR_SIZE} バイト・OAuth 起因ではない可能性）"
            echo "      ${DIM}末尾3行:${RESET}"
            tail -3 "$LAUNCHD_ERR" | sed 's/^/      /'
        fi
    fi
else
    echo "  ${INFO} launchd.err が存在しません（一度も実行されていない？）"
fi

# 4c. launchd.log の末尾 200 行で OAuth 失効を検出
#     upload_today.sh は stderr を grep フィルタしているため、Python トレースバックは
#     launchd.log（stdout 経由のリダイレクト）に残る。ここで拾わないと OAuth 失効を
#     「正常」と誤判定してしまう。
if [ -f "$LAUNCHD_LOG" ]; then
    LOG_MTIME=$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$LAUNCHD_LOG" 2>/dev/null)
    LOG_MTIME_EPOCH=$(stat -f '%m' "$LAUNCHD_LOG" 2>/dev/null)
    echo "  ${INFO} launchd.log 直近更新: $LOG_MTIME"

    if tail -200 "$LAUNCHD_LOG" | grep -E "$OAUTH_PATTERN" >/dev/null 2>&1; then
        if [ "$OAUTH_FAIL" -eq 0 ]; then
            echo "  ${NG} ${RED}OAuth トークン失効を検出（前回アップロード失敗）${RESET}"
            tail -200 "$LAUNCHD_LOG" | grep -E "$OAUTH_PATTERN" | tail -3 | sed 's/^/      /'
        else
            echo "  ${DIM}      （launchd.log にも同様の OAuth 失効痕跡あり）${RESET}"
        fi
        OAUTH_FAIL=1
        launchd_ok=0

        # 終了ステータス 0 だった場合の追加注記（upload_today.sh のフィルタで握り潰された）
        if [ "$LCTL_STATUS" = "0" ]; then
            echo "  ${WARN} ${YELLOW}終了ステータスは 0 だが Python レベルでエラーが発生していた${RESET}"
            echo "      ${DIM}（youtube/upload_today.sh の stderr フィルタが終了コードを握り潰した可能性）${RESET}"
        fi

        # 復旧手順を 3 行表示
        echo
        echo "  ${BOLD}復旧方法（監督の手・3分）:${RESET}"
        echo "    1. rm /Users/don/cheer_tumbling_app/youtube/token.json"
        echo "    2. cd /Users/don/cheer_tumbling_app/youtube && python3 upload_videos.py --only \"___AUTH___\""
        echo "    3. ブラウザが開くので cheernicpro@gmail.com で承認 → 完了"
        echo

        add_todo "OAuth 再認証（token.json 削除 → upload_videos.py --only \"___AUTH___\" で承認フロー）"
    fi
fi

# 4d. uploaded.json と launchd.log の更新時刻比較
#     launchd が走った後に uploaded.json が更新されていなければ「アップロード 0 件」
if [ -f "$LAUNCHD_LOG" ] && [ -f "$UPLOADED_JSON" ] && [ -n "$LOG_MTIME_EPOCH" ]; then
    UPLOADED_MTIME_EPOCH=$(stat -f '%m' "$UPLOADED_JSON" 2>/dev/null)
    UPLOADED_MTIME=$(stat -f '%Sm' -t '%Y-%m-%d %H:%M' "$UPLOADED_JSON" 2>/dev/null)
    echo "  ${INFO} uploaded.json 直近更新: $UPLOADED_MTIME"
    if [ -n "$UPLOADED_MTIME_EPOCH" ] && [ "$UPLOADED_MTIME_EPOCH" -lt "$LOG_MTIME_EPOCH" ]; then
        echo "  ${WARN} ${YELLOW}前回 launchd 実行でアップロード成功 0 件${RESET}"
        echo "      ${DIM}（launchd.log が uploaded.json より新しい＝書き込みなし）${RESET}"
        if [ "$OAUTH_FAIL" -eq 0 ]; then
            add_todo "前回 launchd 実行でアップロード 0 件。launchd.log を確認してください"
        fi
    else
        echo "  ${OK} 前回 launchd 実行後に uploaded.json が更新されています"
    fi
fi
echo

# ─────────────────────────────────────────────────────────
# 5. アプリ反映
# ─────────────────────────────────────────────────────────
echo "${BOLD}── 5. アプリ反映（index.html への youtubeId 記載）──${RESET}"
if [ ! -f index.html ]; then
    echo "  ${NG} index.html が見つかりません"
    add_todo "index.html が存在しません（リポジトリ構造を確認）"
else
    REFLECT_OUT=$(UPLOADED_JSON="$UPLOADED_JSON" python3 - <<'PY'
import json, os
uploaded = json.load(open(os.environ['UPLOADED_JSON']))
html = open('index.html', encoding='utf-8').read()
not_reflected = [v for v in uploaded.values() if v['id'] not in html]
print(f"TOTAL_UP={len(uploaded)}")
print(f"NOT_REFLECTED={len(not_reflected)}")
for v in not_reflected:
    title = v['title'].split('｜')[0]
    print(f"MISS::{title}\t{v['id']}\t{v['url']}")
PY
)
    TOTAL_UP=$(echo "$REFLECT_OUT" | grep '^TOTAL_UP=' | cut -d= -f2)
    NOT_REFLECTED=$(echo "$REFLECT_OUT" | grep '^NOT_REFLECTED=' | cut -d= -f2)
    if [ "$NOT_REFLECTED" -eq 0 ]; then
        echo "  ${OK} アップロード済 ${TOTAL_UP} 本すべて index.html に反映済み"
    else
        echo "  ${WARN} ${YELLOW}index.html 未反映 ${NOT_REFLECTED} 本（youtubeId 追加が必要）${RESET}"
        echo "$REFLECT_OUT" | grep '^MISS::' | sed 's/^MISS:://' | while IFS=$'\t' read -r title id url; do
            echo "      - $title  ${DIM}($id  $url)${RESET}"
        done
        add_todo "index.html の skills/trainings 配列に youtubeId を ${NOT_REFLECTED} 本追加"
    fi
fi
echo

# ─────────────────────────────────────────────────────────
# サマリー：即対応事項
# ─────────────────────────────────────────────────────────
echo "${BOLD}╔══════════════════════════════════════════════════════════════╗${RESET}"
echo "${BOLD}║  サマリー：即対応が必要な事項                                ║${RESET}"
echo "${BOLD}╚══════════════════════════════════════════════════════════════╝${RESET}"
if [ ! -s "$TODO_FILE" ]; then
    echo "  ${OK} ${GREEN}対応事項なし。パイプラインは健全に稼働中です${RESET}"
    exit 0
else
    i=1
    while IFS= read -r line; do
        echo "  ${YELLOW}${i}.${RESET} $line"
        i=$((i + 1))
    done < "$TODO_FILE"
    exit 1
fi
