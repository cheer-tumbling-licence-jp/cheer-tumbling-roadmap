#!/usr/bin/env python3
"""
選手向け特化 A4 チラシ

構成（A4縦・297mm）：
- ヘッダ：協会名 + 「選手向け」バッジ
- ヒーロー：「自分の上達を、見える形に。」+ サブ
- 目玉機能 #1：成長記録ヒートマップ（スクショ大）
- 目玉機能 #2：自分でトレメを作れる（スクショ大）
- その他機能 4カード（ストリーク報酬・105動画・段階別・お知らせ）
- 選手向けプラン一覧（フリー / 個人 / 新サブスク2つ）
- QR + フッタ

出力：マーケティング/pdf/promo_athlete_a4.pdf
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
    # 選手向け！バッジ
    bw, bh = mm(32), mm(9)
    bx = mm(W_MM) - PAD_X - bw
    by = y0
    badge_img = Image.new("RGB", (bw, bh))
    gradient_rect(badge_img, (0, 0, bw, bh), CYAN, (14, 165, 233), "horizontal")
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), radius=mm(4.5), fill=255)
    canvas.paste(badge_img, (bx, by), mask)
    text_centered(d, (bx, by, bx + bw, by + bh), "▸ 選手向け", font(12, bold=True), WHITE)
    return y0 + mm(11)


def draw_hero(canvas, y0):
    d = ImageDraw.Draw(canvas)
    title_f = font(30, bold=True)
    d.text((PAD_X, y0), "自分の上達を、", font=title_f, fill=CYAN)
    _, lh = measure_text(d, "自分の上達を、", title_f)
    y = y0 + lh + mm(1)
    d.text((PAD_X, y), "見える形に。", font=title_f, fill=CYAN)
    y += lh + mm(3)
    d.text((PAD_X, y), "動画で学び、自分でメニューを組み、毎日の練習が記録に残る。",
           font=font(11), fill=TEXT_DARK)
    y += mm(6)
    d.text((PAD_X, y), "30日連続で続けたら、有料動画1本を「永久に」ご褒美として解放！",
           font=font(10, bold=True), fill=ORANGE_DARK)
    return y + mm(7)


def draw_hero_feature(canvas, y0, num, title, desc, shot_path, points, color, is_mobile=False):
    """目玉機能大カード（圧縮版：フッターが確実に入るよう縮小）"""
    d = ImageDraw.Draw(canvas)
    inner_w = mm(W_MM) - PAD_X * 2
    box_h = mm(52) if not is_mobile else mm(60)
    rounded_rect(d, (PAD_X, y0, PAD_X + inner_w, y0 + box_h),
                 mm(3), fill=DARK_BG_2, outline=color, width=3)
    badge_w, badge_h = mm(26), mm(5.5)
    d.rounded_rectangle((PAD_X + mm(3), y0 + mm(2.5), PAD_X + mm(3) + badge_w, y0 + mm(2.5) + badge_h),
                        radius=mm(1.5), fill=color)
    text_centered(d, (PAD_X + mm(3), y0 + mm(2.5), PAD_X + mm(3) + badge_w, y0 + mm(2.5) + badge_h),
                  f"★ 目玉機能 #{num}", font(7.5, bold=True), WHITE)
    img_x0 = PAD_X + mm(3)
    img_y0 = y0 + mm(9.5)
    if is_mobile:
        img_w = mm(34); img_h = mm(48)
    else:
        img_w = mm(80); img_h = mm(40)
    paste_screenshot(canvas, str(shot_path), (img_x0, img_y0, img_x0 + img_w, img_y0 + img_h),
                     radius_mm=2)
    tx = img_x0 + img_w + mm(4)
    ty = y0 + mm(9.5)
    d.text((tx, ty), title, font=font(11, bold=True), fill=WHITE)
    ty += mm(6)
    max_chars = 22 if is_mobile else 26
    lines = []
    cur = ""
    for ch in desc:
        cur += ch
        if len(cur) >= max_chars:
            lines.append(cur); cur = ""
    if cur: lines.append(cur)
    max_lines = 3 if is_mobile else 2
    for ln in lines[:max_lines]:
        d.text((tx, ty), ln, font=font(7.5), fill=(220, 215, 240))
        ty += mm(3.5)
    ty += mm(1.5)
    for pt in points:
        d.rounded_rectangle((tx, ty + mm(0.3), tx + mm(3.5), ty + mm(3.8)),
                            radius=mm(0.8), fill=color)
        text_centered(d, (tx, ty + mm(0.3), tx + mm(3.5), ty + mm(3.8)),
                      "✓", font(6.5, bold=True), WHITE)
        d.text((tx + mm(5), ty + mm(0.7)), pt, font=font(7.5), fill=WHITE)
        ty += mm(4.5)
    return y0 + box_h + mm(3)


def draw_other_features(canvas, y0):
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ 選手ならではの機能",
           font=font(10.5, bold=True), fill=DARK_TEXT)
    y = y0 + mm(5.5)
    inner_w = mm(W_MM) - PAD_X * 2
    col_w = (inner_w - mm(3)) // 2
    row_h = mm(17)
    items = [
        ("30日連続で 動画1本 永久解放", "毎日続けるほど、ご褒美動画が増える", (255, 138, 61)),
        ("解説動画 105本", "全技を動画で学べる。反復再生OK", GREEN),
        ("Lv1〜Lv6 段階別ロードマップ", "今の自分レベルから 次に狙う技が見える", PURPLE),
        ("お知らせで最新情報", "新しい動画や機能をアプリからお知らせ", CYAN),
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
        d.text((cx0 + mm(5), cy0 + mm(2.2)), title, font=font(9.5, bold=True), fill=DARK_TEXT)
        d.text((cx0 + mm(5), cy0 + mm(8.5)), body, font=font(7), fill=TEXT_MUTED)
    return y + row_h * 2 + mm(2) + mm(4)


def draw_pricing(canvas, y0):
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ 選手向けプラン",
           font=font(10.5, bold=True), fill=DARK_TEXT)
    y = y0 + mm(5.5)
    inner_w = mm(W_MM) - PAD_X * 2

    plans = [
        ("フリー", "¥0/月", "動画・トレメ・記録すべて無料", (255, 200, 30), True),
        ("個人", "¥480/月", "プレミアム動画も解放", PURPLE, False),
        ("トレーニング指導 NEW", "¥4,500/月", "個別メニュー + 動画添削月20本", ORANGE, "grad"),
        ("完全1on1 NEW", "¥7,500/月", "添削無制限 + 専用LINE + 月1通話", PINK, "grad"),
    ]
    col_w = (inner_w - mm(3) * 3) // 4
    row_h = mm(18)
    for i, (name, price, desc, color, style) in enumerate(plans):
        cx0 = PAD_X + i * (col_w + mm(3))
        cx1 = cx0 + col_w
        if style is True:  # フリー黄色強調
            rounded_rect(d, (cx0, y, cx1, y + row_h), mm(2),
                         fill=(255, 248, 200), outline=(255, 200, 30), width=2)
            d.text((cx0 + mm(2), y + mm(1)), name, font=font(8, bold=True), fill=(140, 100, 0))
            d.text((cx0 + mm(2), y + mm(5)), price, font=font(11, bold=True), fill=(180, 130, 0))
            d.text((cx0 + mm(2), y + mm(12)), desc, font=font(6), fill=(120, 90, 0))
        elif style == "grad":  # 新サブスク
            bg = Image.new("RGB", (col_w, row_h))
            gradient_rect(bg, (0, 0, col_w, row_h), color, PURPLE_DARK if color == PINK else ORANGE_DARK, "diag")
            mask = Image.new("L", (col_w, row_h), 0)
            ImageDraw.Draw(mask).rounded_rectangle((0, 0, col_w, row_h), radius=mm(2), fill=255)
            canvas.paste(bg, (cx0, y), mask)
            d.text((cx0 + mm(2), y + mm(1)), name, font=font(7, bold=True), fill=WHITE)
            d.text((cx0 + mm(2), y + mm(5)), price, font=font(10, bold=True), fill=WHITE)
            d.text((cx0 + mm(2), y + mm(12)), desc, font=font(6), fill=WHITE)
        else:
            rounded_rect(d, (cx0, y, cx1, y + row_h), mm(2),
                         fill=BG_PURPLE_SOFT, outline=BORDER, width=1)
            d.text((cx0 + mm(2), y + mm(1)), name, font=font(8, bold=True), fill=DARK_TEXT)
            d.text((cx0 + mm(2), y + mm(5)), price, font=font(11, bold=True), fill=color)
            d.text((cx0 + mm(2), y + mm(12)), desc, font=font(6), fill=TEXT_MUTED)
    y += row_h + mm(2)
    d.text((PAD_X, y), "※ フリー・個人はすぐ利用開始／新サブスク（¥4,500 / ¥7,500）は先行受付中",
           font=font(6.5), fill=TEXT_MUTED)
    return y + mm(4)


def draw_footer(canvas, y0):
    d = ImageDraw.Draw(canvas)
    inner_w = mm(W_MM) - PAD_X * 2

    cta_h = mm(13)
    cta_img = Image.new("RGB", (inner_w, cta_h))
    gradient_rect(cta_img, (0, 0, inner_w, cta_h), CYAN, PURPLE, "horizontal")
    mask = Image.new("L", (inner_w, cta_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, inner_w, cta_h), radius=mm(2.5), fill=255)
    canvas.paste(cta_img, (PAD_X, y0), mask)
    text_centered(d, (PAD_X, y0, PAD_X + inner_w, y0 + cta_h - mm(4)),
                  "▶ QR で読み取って、今すぐ始めよう",
                  font(15, bold=True), WHITE)
    text_centered(d, (PAD_X, y0 + cta_h - mm(5), PAD_X + inner_w, y0 + cta_h),
                  "（アカウント登録なしでも、まず技リストと動画は見られます）",
                  font(8.5), (255, 235, 200))
    y = y0 + cta_h + mm(3)

    qr_size = mm(32)
    qr_path = OUT_DIR / "_promo_qr.png"
    gen_qr_png_hi("https://roadmap.cheer-tumbling.jp/", str(qr_path))
    draw_qr_box(canvas, (PAD_X, y, PAD_X + qr_size, y + qr_size), str(qr_path))
    tx = PAD_X + qr_size + mm(5)
    d.text((tx, y + mm(0.5)), "スマホのカメラで QR を読み取り", font=font(10, bold=True), fill=DARK_TEXT)
    d.text((tx, y + mm(6.5)), "roadmap.cheer-tumbling.jp", font=font(13, bold=True), fill=CYAN)
    d.text((tx, y + mm(14)), "iPhone: Safari ／ Android: Chrome", font=font(7.5), fill=TEXT_MUTED)
    d.text((tx, y + mm(18)), "監修：中村 祐介（指導歴18年・元体操選手）", font=font(7), fill=TEXT_MUTED)
    d.text((tx, y + mm(22)), "　　　前島 一貴（国際ライセンス保有）", font=font(7), fill=TEXT_MUTED)
    d.text((tx, y + mm(26)), "発行：一般社団法人 チアタンブリング協会", font=font(6.5), fill=TEXT_MUTED)


def make_athlete_flyer():
    img = make_canvas(W_MM, H_MM)
    y = mm(6)
    y = draw_header(img, y)
    y = draw_hero(img, y)

    y = draw_hero_feature(
        img, y, num=1,
        title="成長記録ヒートマップで、自分の伸びが見える",
        desc="達成率・習得済み・あと少しの技を色で可視化。頑張った日が色で塗られ、続けたくなる。",
        shot_path=SHOTS / "desktop" / "02_progress_heatmap.png",
        points=[
            "全体の達成率がひと目でわかる",
            "「あと少し」の技を狙って練習できる",
            "頑張った日が色で残り、続くのが楽しい",
        ],
        color=CYAN,
    )
    y = draw_hero_feature(
        img, y, num=2,
        title="自分のメニューを、自分で作れる",
        desc="技とトレーニングを組み合わせて、自分だけの練習メニューを保存。秒数・回数も指定可能。チームに共有もできる。",
        shot_path=SHOTS / "mobile" / "04_practice_menu.png",
        points=[
            "スキル33 + トレ44から選んで組み合わせ",
            "秒数・回数まで自由に設定",
            "作ったメニューはチームに共有可能",
        ],
        color=PURPLE,
        is_mobile=True,
    )
    y = draw_other_features(img, y)
    y = draw_pricing(img, y)
    draw_footer(img, y)

    out_png = OUT_DIR / "promo_athlete_a4.png"
    out_pdf = OUT_DIR / "promo_athlete_a4.pdf"
    img.save(out_png, "PNG", dpi=(DPI, DPI))
    img.save(out_pdf, "PDF", resolution=DPI)
    print(f"✓ {out_png}")
    print(f"✓ {out_pdf}")


if __name__ == "__main__":
    make_athlete_flyer()
