#!/usr/bin/env python3
"""
A4 表裏 2ページPDF：表 = 総合告知 / 裏 = コーチ機能特化

既存の promo_general_a4.png と promo_coach_a4.png を1本のPDFに結合。
それぞれ最新版を再生成してから結合する。

出力：マーケティング/pdf/promo_2page_a4.pdf
"""
import sys
from pathlib import Path
from PIL import Image

sys.path.insert(0, str(Path(__file__).parent))
from make_print_flyer import DPI
from make_promo_general_flyer import make_promo_general
from make_promo_coach_flyer import make_coach_flyer

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "マーケティング" / "pdf"

# 最新版を再生成
make_promo_general()
make_coach_flyer()

# PNG を PDF に結合
p1 = Image.open(OUT_DIR / "promo_general_a4.png").convert("RGB")
p2 = Image.open(OUT_DIR / "promo_coach_a4.png").convert("RGB")

out = OUT_DIR / "promo_2page_a4.pdf"
p1.save(out, "PDF", save_all=True, append_images=[p2], resolution=DPI)
print(f"✓ {out} (表：総合告知 / 裏：コーチ機能特化)")
