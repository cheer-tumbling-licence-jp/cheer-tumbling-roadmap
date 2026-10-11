#!/usr/bin/env python3
"""著者指定の現場用語ルール違反を検出する。

使い方: python3 check_wording.py <ファイル>
終了コード: 0 = 違反なし（警告のみは 0）/ 1 = 違反あり

誤検知を避けるため 2 段階に分ける:
  違反   … 禁止語をそのまま使っている → ブロック
  要確認 … 「〜は厳禁」のように禁止語を打ち消す文脈で出てきた → 警告のみ
"""
import re
import sys
import pathlib

# (正規表現, 指摘内容)
RULES = [
    (r"弾く|弾ける|弾ん[でだ]|弾む", "「弾く」系は使わない → 「体を伸ばす」"),
    (r"伸び上が", "「伸び上がる」は使わない → 「体を伸ばす」"),
    (r"一瞬ためて|一瞬タメて|一瞬溜めて", "「一瞬ためて」→ 「脚に体重を感じて」"),
    (r"下手", "「下手」は使用禁止 → 動作・メカニズムで表現"),
    (r"(?<![アス])タック(?!ル)", "「タック」→ 「抱え込み」"),
    (r"椅子に座るよう|イスに座るよう", "床反力が逆になる誤った声がけ"),
]

# この語が同じ行にあれば「禁止語を戒めている文」とみなし、警告どまりにする
NEGATION = re.compile(r"厳禁|禁止|NG|間違|誤っ|避け|ではなく|してはいけない|ダメ|逆効果|よくある失敗")

# 画面に表示されない裏フィールド（YouTube 検索語など）は対象外
HIDDEN_FIELD = re.compile(r"""^\s*(query|youtubeId|id|nameEn)\s*:""")


def scan(path):
    src = pathlib.Path(path).read_text(encoding="utf-8", errors="replace")
    violations, warnings = [], []
    for i, line in enumerate(src.split("\n"), 1):
        if HIDDEN_FIELD.match(line):
            continue
        # 行の途中にある query: '...' も除外する
        stripped = re.sub(r"""query\s*:\s*(['"]).*?\1""", "", line)
        for pat, desc in RULES:
            m = re.search(pat, stripped)
            if not m:
                continue
            hit = (i, m.group(0), desc, stripped.strip()[:70])
            (warnings if NEGATION.search(stripped) else violations).append(hit)
    return violations, warnings


def dump(label, mark, hits, name):
    print("  %s %s %d 件:" % (mark, label, len(hits)))
    for ln, word, desc, ctx in hits[:20]:
        print("    %s:%d  「%s」 — %s" % (name, ln, word, desc))
        print("      > %s" % ctx)
    if len(hits) > 20:
        print("    …ほか %d 件" % (len(hits) - 20))


def main():
    path = pathlib.Path(sys.argv[1])
    violations, warnings = scan(path)

    if warnings:
        dump("要確認（禁止語を戒めている文に見える）", "⚠️ ", warnings, path.name)
    if violations:
        dump("違反", "❌", violations, path.name)
        return 1
    if not warnings:
        print("  ✅ 違反なし")
    else:
        print("  ✅ 違反なし（上記は警告のみ）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
