#!/usr/bin/env python3
"""標準入力の HTML から技データ領域（EDITABLE_DATA）のハッシュを出す。

マーカーが無ければ NOTFOUND。
"""
import hashlib
import re
import sys

src = sys.stdin.read()
m = re.search(r"=== EDITABLE_DATA_START ===(.*?)=== EDITABLE_DATA_END ===", src, re.S)
print(hashlib.sha256(m.group(1).encode()).hexdigest()[:16] if m else "NOTFOUND")
