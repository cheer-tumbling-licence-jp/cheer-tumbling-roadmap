#!/usr/bin/env python3
"""
保護者向け特化 A4 チラシ

構成（A4縦・297mm）：
- ヘッダ：協会名 + 「保護者向け」バッジ
- ヒーロー：「お子様の練習を、安心して見守れる。」+ サブ
- 目玉機能 #1：段階性と安全評価（技詳細スクショ）
- 目玉機能 #2：成長記録の閲覧（ヒートマップ）
- 保護者に安心の 4カード（監修者権威・段階別・危険度明示・国際ライセンス）
- 保護者向けプラン一覧（フリー / 個人 / 新サブスク2つ）
- QR + フッタ

出力：マーケティング/pdf/promo_parent_a4.pdf
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).parent))
from make_print_flyer import (
    DPI, mm,
    PURPLE, PURPLE_DARK, PINK, CYAN, GOLD,
    DARK_BG, DARK_BG_2, WHITE, TEXT_DIM, TEXT_MUTED, TEXT_DARK,
    BG_PURPLE_SOFT, BG_CYAN_SOFT, BORDER,
    ORANGE, ORANGE_DARK, ORANGE_LIGHT,
    gradient_rect, rounded_rect, text_centered, measure_text, make_canvas,
)
from make_promo_general_flyer import (
    font, paste_screenshot, draw_qr_box, gen_qr_png_hi,
    GREEN, BLUE, RED_NEW, GRAY_BORDER, DARK_TEXT,
)

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "マーケティング" / "pdf"
OUT_DIR.mkdir(exist_ok=True)
SHOTS = ROOT / "assets" / "lp-screenshots"

W_MM, H_MM = 210, 297
PAD_X = mm(10)


def draw_header(canvas, y0):
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0 + mm(2)), "一般社団法人 チアタンブリング協会  公式アプリ",
           font=font(8.5), fill=TEXT_MUTED)
    bw, bh = mm(32), mm(9)
    bx = mm(W_MM) - PAD_X - bw
    by = y0
    badge_img = Image.new("RGB", (bw, bh))
    gradient_rect(badge_img, (0, 0, bw, bh), PINK, (219, 39, 119), "horizontal")
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), radius=mm(4.5), fill=255)
    canvas.paste(badge_img, (bx, by), mask)
    text_centered(d, (bx, by, bx + bw, by + bh), "▸ 保護者向け", font(12, bold=True), WHITE)
    return y0 + mm(11)


def draw_hero(canvas, y0):
    d = ImageDraw.Draw(canvas)
    title_f = font(28, bold=True)
    d.text((PAD_X, y0), "お子様の練習を、", font=title_f, fill=(219, 39, 119))
    _, lh = measure_text(d, "お子様の練習を、", title_f)
    y = y0 + lh + mm(1)
    d.text((PAD_X, y), "安心して見守れる。", font=title_f, fill=(219, 39, 119))
    y += lh + mm(3)
    d.text((PAD_X, y), "指導歴18年のプロと国際ライセンス保有者の監修。",
           font=font(11, bold=True), fill=TEXT_DARK)
    y += mm(6)
    d.text((PAD_X, y), "段階性と安全評価に基づいた練習で、無理のない上達をサポートします。",
           font=font(10), fill=TEXT_MUTED)
    return y + mm(7)


def draw_hero_feature(canvas, y0, num, title, desc, shot_path, points, color, is_mobile=False):
    d = ImageDraw.Draw(canvas)
    inner_w = mm(W_MM) - PAD_X * 2
    box_h = mm(66) if not is_mobile else mm(78)
    rounded_rect(d, (PAD_X, y0, PAD_X + inner_w, y0 + box_h),
                 mm(3), fill=DARK_BG_2, outline=color, width=3)
    badge_w, badge_h = mm(28), mm(6)
    d.rounded_rectangle((PAD_X + mm(3), y0 + mm(3), PAD_X + mm(3) + badge_w, y0 + mm(3) + badge_h),
                        radius=mm(1.5), fill=color)
    text_centered(d, (PAD_X + mm(3), y0 + mm(3), PAD_X + mm(3) + badge_w, y0 + mm(3) + badge_h),
                  f"★ 目玉機能 #{num}", font(8, bold=True), WHITE)
    img_x0 = PAD_X + mm(3)
    img_y0 = y0 + mm(11)
    if is_mobile:
        img_w = mm(40); img_h = mm(64)
    else:
        img_w = mm(90); img_h = mm(52)
    paste_screenshot(canvas, str(shot_path), (img_x0, img_y0, img_x0 + img_w, img_y0 + img_h),
                     radius_mm=2)
    tx = img_x0 + img_w + mm(4)
    ty = y0 + mm(11)
    d.text((tx, ty), title, font=font(12, bold=True), fill=WHITE)
    ty += mm(7)
    max_chars = 20 if is_mobile else 24
    lines = []
    cur = ""
    for ch in desc:
        cur += ch
        if len(cur) >= max_chars:
            lines.append(cur); cur = ""
    if cur: lines.append(cur)
    max_lines = 4 if is_mobile else 3
    for ln in lines[:max_lines]:
        d.text((tx, ty), ln, font=font(8), fill=(220, 215, 240))
        ty += mm(4)
    ty += mm(2)
    for pt in points:
        d.rounded_rectangle((tx, ty + mm(0.5), tx + mm(4), ty + mm(4.5)),
                            radius=mm(1), fill=color)
        text_centered(d, (tx, ty + mm(0.5), tx + mm(4), ty + mm(4.5)),
                      "✓", font(7, bold=True), WHITE)
        d.text((tx + mm(6), ty + mm(1)), pt, font=font(8), fill=WHITE)
        ty += mm(5.5)
    return y0 + box_h + mm(4)


def draw_other_features(canvas, y0):
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ 保護者に安心のポイント",
           font=font(11, bold=True), fill=DARK_TEXT)
    y = y0 + mm(6)
    inner_w = mm(W_MM) - PAD_X * 2
    col_w = (inner_w - mm(3)) // 2
    row_h = mm(21)
    items = [
        ("プロ2名による監修", "指導歴18年の中村 祐介と、国際ライセンス保有の前島 一貴", PURPLE),
        ("段階性のあるロードマップ", "Lv1〜Lv6 のやさしい級分けで、飛び級のない上達順序", CYAN),
        ("技ごとの危険度を明示", "「危険度：大」「補助必須」など、練習前に必ず確認できる", (219, 39, 119)),
        ("成長記録の閲覧", "お子様の達成率・練習の継続日数がひと目でわかる", GREEN),
    ]
    for i, (title, body, color) in enumerate(items):
        col = i % 2
        row = i // 2
        cx0 = PAD_X + col * (col_w + mm(3))
        cy0 = y + row * (row_h + mm(2))
        rounded_rect(d, (cx0, cy0, cx0 + col_w, cy0 + row_h),
                     mm(2), fill=WHITE, outline=GRAY_BORDER, width=1)
        side_img = Image.new("RGB", (mm(3.5), row_h))
        gradient_rect(side_img, (0, 0, mm(3.5), row_h), color, color, "vertical")
        side_mask = Image.new("L", (mm(3.5), row_h), 0)
        ImageDraw.Draw(side_mask).rounded_rectangle((0, 0, mm(3.5), row_h), radius=mm(2), fill=255)
        canvas.paste(side_img, (cx0, cy0), side_mask)
        d.text((cx0 + mm(5), cy0 + mm(2.5)), title, font=font(10, bold=True), fill=DARK_TEXT)
        d.text((cx0 + mm(5), cy0 + mm(9)), body, font=font(7.5), fill=TEXT_MUTED)
    return y + row_h * 2 + mm(2) + mm(5)


def draw_pricing(canvas, y0):
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ プランは、お子様の目標に合わせて",
           font=font(11, bold=True), fill=DARK_TEXT)
    y = y0 + mm(6)
    inner_w = mm(W_MM) - PAD_X * 2

    plans = [
        ("フリー", "¥0/月", "動画・トレメ・記録すべて無料", (255, 200, 30), True),
        ("個人", "¥480/月", "プレミアム動画も解放", PURPLE, False),
        ("トレーニング指導 NEW", "¥4,500/月", "個別メニュー + 動画添削月20本", ORANGE, "grad"),
        ("完全1on1 NEW", "¥7,500/月", "添削無制限 + 専用LINE + 月1通話", PINK, "grad"),
    ]
    col_w = (inner_w - mm(3) * 3) // 4
    row_h = mm(22)
    for i, (name, price, desc, color, style) in enumerate(plans):
        cx0 = PAD_X + i * (col_w + mm(3))
        cx1 = cx0 + col_w
        if style is True:
            rounded_rect(d, (cx0, y, cx1, y + row_h), mm(2),
                         fill=(255, 248, 200), outline=(255, 200, 30), width=2)
            d.text((cx0 + mm(2), y + mm(1.5)), name, font=font(9, bold=True), fill=(140, 100, 0))
            d.text((cx0 + mm(2), y + mm(6.5)), price, font=font(13, bold=True), fill=(180, 130, 0))
            d.text((cx0 + mm(2), y + mm(15)), desc, font=font(6.5), fill=(120, 90, 0))
        elif style == "grad":
            bg = Image.new("RGB", (col_w, row_h))
            gradient_rect(bg, (0, 0, col_w, row_h), color, PURPLE_DARK if color == PINK else ORANGE_DARK, "diag")
            mask = Image.new("L", (col_w, row_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, col_w, row_h), radius=mm(2), fill=255)
            canvas.paste(bg, (cx0, y), mask)
            d.text((cx0 + mm(2), y + mm(1.5)), name, font=font(7.5, bold=True), fill=WHITE)
            d.text((cx0 + mm(2), y + mm(6.5)), price, font=font(11, bold=True), fill=WHITE)
            d.text((cx0 + mm(2), y + mm(15)), desc, font=font(6.5), fill=WHITE)
        else:
            rounded_rect(d, (cx0, y, cx1, y + row_h), mm(2),
                         fill=BG_PURPLE_SOFT, outline=BORDER, width=1)
            d.text((cx0 + mm(2), y + mm(1.5)), name, font=font(9, bold=True), fill=DARK_TEXT)
            d.text((cx0 + mm(2), y + mm(6.5)), price, font=font(13, bold=True), fill=color)
            d.text((cx0 + mm(2), y + mm(15)), desc, font=font(6.5), fill=TEXT_MUTED)
    y += row_h + mm(3)
    d.text((PAD_X, y), "※ まずは無料プランで、お子様に合うかを試せます。",
           font=font(7), fill=TEXT_MUTED)
    return y + mm(5)


def draw_footer(canvas, y0):
    d = ImageDraw.Draw(canvas)
    inner_w = mm(W_MM) - PAD_X * 2

    cta_h = mm(13)
    cta_img = Image.new("RGB", (inner_w, cta_h))
    gradient_rect(cta_img, (0, 0, inner_w, cta_h), (219, 39, 119), PURPLE_DARK, "horizontal")
    mask = Image.new("L", (inner_w, cta_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, inner_w, cta_h), radius=mm(2.5), fill=255)
    canvas.paste(cta_img, (PAD_X, y0), mask)
    text_centered(d, (PAD_X, y0, PAD_X + inner_w, y0 + cta_h - mm(4)),
                  "▶ QR で、まず無料で試してみてください",
                  font(14, bold=True), WHITE)
    text_centered(d, (PAD_X, y0 + cta_h - mm(5), PAD_X + inner_w, y0 + cta_h),
                  "（クレジット登録なし・動画閲覧・記録すべて無料で使えます）",
                  font(8.5), (255, 235, 200))
    y = y0 + cta_h + mm(3)

    qr_size = mm(32)
    qr_path = OUT_DIR / "_promo_qr.png"
    gen_qr_png_hi("https://roadmap.cheer-tumbling.jp/", str(qr_path))
    draw_qr_box(canvas, (PAD_X, y, PAD_X + qr_size, y + qr_size), str(qr_path))
    tx = PAD_X + qr_size + mm(5)
    d.text((tx, y + mm(0.5)), "スマホのカメラで QR を読み取り", font=font(10, bold=True), fill=DARK_TEXT)
    d.text((tx, y + mm(6.5)), "roadmap.cheer-tumbling.jp", font=font(13, bold=True), fill=(219, 39, 119))
    d.text((tx, y + mm(14)), "iPhone: Safari ／ Android: Chrome", font=font(7.5), fill=TEXT_MUTED)
    d.text((tx, y + mm(18)), "監修：中村 祐介（指導歴18年・元体操選手）", font=font(7), fill=TEXT_MUTED)
    d.text((tx, y + mm(22)), "　　　前島 一貴（国際ライセンス保有）", font=font(7), fill=TEXT_MUTED)
    d.text((tx, y + mm(26)), "発行：一般社団法人 チアタンブリング協会", font=font(6.5), fill=TEXT_MUTED)


def make_parent_flyer():
    img = make_canvas(W_MM, H_MM)
    y = mm(6)
    y = draw_header(img, y)
    y = draw_hero(img, y)

    y = draw_hero_feature(
        img, y, num=1,
        title="技ごとの危険度と段階性が、ひと目でわかる",
        desc="各技には「Lv1〜Lv6」の段階と「危険度」が明示。無理な飛び級を避け、必ず前段階のスキルから練習する構成です。",
        shot_path=SHOTS / "mobile" / "03_skill_detail.png",
        points=[
            "各技に段階レベル（Lv1〜Lv6）を明示",
            "「危険度：大」「補助必須」を練習前に確認",
            "前段階スキル・つまずきポイントを明示",
        ],
        color=(219, 39, 119),
        is_mobile=True,
    )
    y = draw_hero_feature(
        img, y, num=2,
        title="お子様の成長を、記録で見守れる",
        desc="達成した技・練習中の技・継続日数をグラフとヒートマップで確認。頑張った日は色で塗られ、モチベーションもサポート。",
        shot_path=SHOTS / "desktop" / "02_progress_heatmap.png",
        points=[
            "達成率と継続日数がひと目でわかる",
            "「あと少し」の技も把握できる",
            "お子様の頑張りが「見える化」される",
        ],
        color=CYAN,
    )
    y = draw_other_features(img, y)
    y = draw_pricing(img, y)
    draw_footer(img, y)

    out_png = OUT_DIR / "promo_parent_a4.png"
    out_pdf = OUT_DIR / "promo_parent_a4.pdf"
    img.save(out_png, "PNG", dpi=(DPI, DPI))
    img.save(out_pdf, "PDF", resolution=DPI)
    print(f"✓ {out_png}")
    print(f"✓ {out_pdf}")


if __name__ == "__main__":
    make_parent_flyer()
