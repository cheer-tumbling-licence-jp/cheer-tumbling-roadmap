#!/usr/bin/env python3
"""LP 埋め込み用にスクショを軽量化（PNG→JPEG、リサイズ、quality 85）"""
from PIL import Image
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "assets" / "lp-screenshots"
OUT = SRC / "web"

OUT.mkdir(exist_ok=True)
(OUT / "mobile").mkdir(exist_ok=True)
(OUT / "desktop").mkdir(exist_ok=True)

for src_dir, max_w in [("mobile", 600), ("desktop", 1400)]:
    for p in sorted((SRC / src_dir).glob("*.png")):
        img = Image.open(p).convert("RGB")
        scale = max_w / img.width
        new_size = (int(img.width * scale), int(img.height * scale))
        img = img.resize(new_size, Image.LANCZOS)
        out_path = OUT / src_dir / (p.stem + ".jpg")
        img.save(out_path, "JPEG", quality=85, optimize=True)
        size_kb = out_path.stat().st_size // 1024
        print(f"  ✓ {src_dir}/{p.stem}.jpg  ({new_size[0]}x{new_size[1]}, {size_kb}KB)")
