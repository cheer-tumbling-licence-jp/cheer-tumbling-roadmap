#!/bin/bash
# 完全1on1プラン ¥19,800 の Stripe 価格を作成する
# 使い方：このファイルを Finder でダブルクリック
cd "$(dirname "$0")/functions" || { echo "フォルダが見つかりません"; read -n1; exit 1; }

# nvm 環境の node にパスを通す
export PATH="$HOME/.nvm/versions/node/v24.15.0/bin:$PATH"

clear
echo "============================================"
echo " 完全1on1プラン ¥19,800 の価格を作成します"
echo "============================================"
echo
echo "Stripe のシークレットキー（sk_live_ で始まる文字列）を"
echo "貼り付けて Enter を押してください。"
echo
echo "※ 安全のため、貼り付けても画面には何も表示されません。"
echo "   貼り付けたら、そのまま Enter を押してください。"
echo
printf "キー: "
read -s STRIPE_KEY
echo
echo

if [ -z "$STRIPE_KEY" ]; then
  echo "❌ キーが入力されていません。もう一度ダブルクリックしてやり直してください。"
  echo
  echo "何かキーを押すと閉じます..."
  read -n1
  exit 1
fi

case "$STRIPE_KEY" in
  sk_live_*)
    echo "✅ 本番環境のキーを確認しました。処理を開始します..."
    echo
    ;;
  sk_test_*)
    echo "❌ これはテスト環境のキーです（sk_test_ で始まっています）。"
    echo "   Stripe の画面が「テスト環境」になっていないか確認して、"
    echo "   本番環境のキー（sk_live_）を貼り直してください。"
    echo
    echo "何かキーを押すと閉じます..."
    read -n1
    exit 1
    ;;
  *)
    echo "❌ Stripe のシークレットキーではないようです。"
    echo "   sk_live_ で始まる文字列を貼り付けてください。"
    echo
    echo "何かキーを押すと閉じます..."
    read -n1
    exit 1
    ;;
esac

STRIPE_SECRET_KEY="$STRIPE_KEY" node scripts/setup-stripe-products.js
STATUS=$?
unset STRIPE_KEY STRIPE_SECRET_KEY

echo
echo "============================================"
if [ $STATUS -eq 0 ]; then
  echo " ✅ 完了しました"
  echo
  echo " 上に出ている training_1on1 の price_... を"
  echo " Claude に伝えてください。"
else
  echo " ❌ エラーが出ました"
  echo
  echo " 上のエラー文をそのまま Claude に伝えてください。"
fi
echo "============================================"
echo
echo "何かキーを押すと閉じます..."
read -n1
