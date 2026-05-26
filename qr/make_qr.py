"""
Cheer Tumbling Roadmap 用 QR コード生成スクリプト
- ピンク × 紫グラデーションでドットを着色
- 中央に空白を確保（ロゴ用余白）
- 印刷向け（300dpi 相当）と、SNS / 名刺向けの 2 サイズを書き出し
"""
from __future__ import annotations
import os
from PIL import Image, ImageDraw, ImageFont
import qrcode
from qrcode.constants import ERROR_CORRECT_H

URL = "https://roadmap.cheer-tumbling.jp/"
OUT_DIR = os.path.dirname(os.path.abspath(__file__))

# テーマカラー
PINK = (255, 77, 143)
PURPLE = (168, 85, 247)
CYAN = (6, 214, 248)
BG = (255, 255, 255)


def gradient_color(t: float) -> tuple[int, int, int]:
    """t in [0,1] → ピンク→紫→シアンの 3 色グラデを返す"""
    if t < 0.5:
        u = t / 0.5
        r = int(PINK[0] + (PURPLE[0] - PINK[0]) * u)
        g = int(PINK[1] + (PURPLE[1] - PINK[1]) * u)
        b = int(PINK[2] + (PURPLE[2] - PINK[2]) * u)
    else:
        u = (t - 0.5) / 0.5
        r = int(PURPLE[0] + (CYAN[0] - PURPLE[0]) * u)
        g = int(PURPLE[1] + (CYAN[1] - PURPLE[1]) * u)
        b = int(PURPLE[2] + (CYAN[2] - PURPLE[2]) * u)
    return (r, g, b)


def make_qr(out_path: str, box_size: int, border: int, with_caption: bool):
    qr = qrcode.QRCode(
        version=None,
        error_correction=ERROR_CORRECT_H,  # ロゴ・装飾耐性のため High
        box_size=box_size,
        border=border,
    )
    qr.add_data(URL)
    qr.make(fit=True)
    matrix = qr.get_matrix()

    n = len(matrix)
    size = (n + border * 2) * box_size
    img = Image.new("RGBA", (size, size), BG + (255,))
    draw = ImageDraw.Draw(img)

    cx = cy = (n - 1) / 2.0
    max_d = ((cx) ** 2 + (cy) ** 2) ** 0.5

    for r, row in enumerate(matrix):
        for c, v in enumerate(row):
            if not v:
                continue
            # 中央正方形（縦横それぞれ全体の 18%）はロゴ用に空白化
            if abs(r - cx) < n * 0.09 and abs(c - cy) < n * 0.09:
                continue
            d = ((r - cx) ** 2 + (c - cy) ** 2) ** 0.5
            color = gradient_color(d / max_d)
            x0 = (c + border) * box_size
            y0 = (r + border) * box_size
            x1 = x0 + box_size
            y1 = y0 + box_size
            # 角丸の小さな四角でドットを描く
            radius = max(1, box_size // 4)
            draw.rounded_rectangle([x0 + 1, y0 + 1, x1 - 1, y1 - 1], radius=radius, fill=color)

    # 中央のロゴ用に丸い土台を描く
    cs = int(size * 0.18)
    cx_px = size // 2
    cy_px = size // 2
    draw.ellipse(
        [cx_px - cs // 2, cy_px - cs // 2, cx_px + cs // 2, cy_px + cs // 2],
        fill=(255, 255, 255, 255),
        outline=PINK + (255,),
        width=max(2, box_size // 3),
    )
    # 中央にハートマーク（チア感）
    heart_size = int(cs * 0.55)
    draw_heart(draw, cx_px, cy_px + heart_size // 12, heart_size, PINK)

    if with_caption:
        # キャプション（タイトル + URL）を下に追加
        caption_h = int(size * 0.16)
        new_img = Image.new("RGBA", (size, size + caption_h), BG + (255,))
        new_img.paste(img, (0, 0))
        d2 = ImageDraw.Draw(new_img)
        title = "Cheer Tumbling Roadmap"
        sub = URL.replace("https://", "")
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(caption_h * 0.34))
            url_font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", int(caption_h * 0.20))
        except OSError:
            title_font = ImageFont.load_default()
            url_font = ImageFont.load_default()

        tw = d2.textlength(title, font=title_font)
        d2.text(((size - tw) / 2, size + caption_h * 0.15), title, fill=PURPLE, font=title_font)
        uw = d2.textlength(sub, font=url_font)
        d2.text(((size - uw) / 2, size + caption_h * 0.6), sub, fill=(110, 100, 140), font=url_font)
        img = new_img

    img.save(out_path)
    print(f"  → {out_path}  ({img.size[0]}×{img.size[1]} px)")


def draw_heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color: tuple[int, int, int]):
    """シンプルなハート形（2つの円 + 三角）"""
    r = size // 4
    # 左右の上半円
    draw.ellipse([cx - r * 2, cy - r * 2, cx, cy], fill=color + (255,))
    draw.ellipse([cx, cy - r * 2, cx + r * 2, cy], fill=color + (255,))
    # 下の三角形
    draw.polygon(
        [
            (cx - r * 2 + r // 4, cy - r // 2),
            (cx + r * 2 - r // 4, cy - r // 2),
            (cx, cy + r * 2),
        ],
        fill=color + (255,),
    )


if __name__ == "__main__":
    print("QR コード生成中...")
    # 印刷向け（高解像度・大）
    make_qr(os.path.join(OUT_DIR, "qr_print.png"), box_size=24, border=4, with_caption=True)
    # SNS / 名刺向け（中サイズ・キャプションつき）
    make_qr(os.path.join(OUT_DIR, "qr_share.png"), box_size=14, border=4, with_caption=True)
    # アイコン用（最小・キャプションなし）
    make_qr(os.path.join(OUT_DIR, "qr_icon.png"), box_size=10, border=3, with_caption=False)
    print("完了")
