#!/usr/bin/env python3
"""index.html のインライン <script> を抽出して個別ファイルに書き出す。

使い方: python3 extract_inline_js.py <html> <出力ディレクトリ>
標準出力に抽出したブロック数を出す。
"""
import re
import sys
import pathlib

src = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
out = pathlib.Path(sys.argv[2])

JS_TYPES = ("text/javascript", "application/javascript", "module")
n = 0
for m in re.finditer(r"<script(?P<attrs>[^>]*)>(?P<body>.*?)</script>", src, re.S | re.I):
    attrs = m.group("attrs")
    if "src=" in attrs.lower():
        continue
    t = re.search(r"""type\s*=\s*["']([^"']+)["']""", attrs, re.I)
    kind = t.group(1).strip().lower() if t else "text/javascript"
    # application/json や text/template などは JS ではないので対象外
    if kind not in JS_TYPES:
        continue
    line = src[: m.start()].count("\n") + 1
    n += 1
    ext = "mjs" if kind == "module" else "js"
    (out / f"block_{n:02d}_line{line}.{ext}").write_text(m.group("body"), encoding="utf-8")

print(n)
