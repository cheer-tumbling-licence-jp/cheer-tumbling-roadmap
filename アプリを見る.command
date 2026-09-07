#!/bin/bash
# ローカルのアプリを Chrome で開く（ダブルクリックで実行）
cd "$(dirname "$0")" || exit 1
PORT=5191

# すでに動いていれば使い回す
if ! curl -s -o /dev/null "http://localhost:$PORT/index.html"; then
  python3 -m http.server $PORT --bind 127.0.0.1 >/dev/null 2>&1 &
  SERVER_PID=$!
  for i in $(seq 1 20); do
    curl -s -o /dev/null "http://localhost:$PORT/index.html" && break
    sleep 0.3
  done
fi

open -a "Google Chrome" "http://localhost:$PORT/index.html?v=$(date +%s)"

clear
echo "============================================"
echo " アプリを Chrome で開きました"
echo "============================================"
echo
echo "  http://localhost:$PORT/index.html"
echo
echo " 見るところ："
echo "   バク転 → 詳細を見る → こんな悩みありませんか"
echo "   → 足が開いてしまう → 直し方ページ"
echo
echo "--------------------------------------------"
echo " このウィンドウは開いたままにしてください。"
echo " 閉じるか Control+C を押すと、アプリが"
echo " 見られなくなります。"
echo "--------------------------------------------"
echo
if [ -n "$SERVER_PID" ]; then
  trap 'kill $SERVER_PID 2>/dev/null' EXIT
  wait $SERVER_PID
else
  echo "何かキーを押すと閉じます..."
  read -n1
fi
