#!/usr/bin/env python3
"""
コーチ向け特化 A4 チラシ

構成（A4縦・297mm）：
- ヘッダ：協会名 + 「コーチ向け」バッジ
- ヒーロー：「コーチの仕事を、半分に。」+ サブ
- 目玉機能 #1：練習プログラム自動生成 → 指導配置図（スクショ大）
- 目玉機能 #2：進捗ヒートマップで全員一望（スクショ大）
- その他コーチ機能 4カード（コンパクト）
- コーチ向けプラン一覧（コーチ¥1,200 / コーチプラス¥1,980 / 新2）
- QR + 監修者 + フッタ

出力：マーケティング/pdf/promo_coach_a4.pdf
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
    # コーチ向け！バッジ
    bw, bh = mm(32), mm(9)
    bx = mm(W_MM) - PAD_X - bw
    by = y0
    badge_img = Image.new("RGB", (bw, bh))
    gradient_rect(badge_img, (0, 0, bw, bh), PURPLE_DARK, PINK, "horizontal")
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), radius=mm(4.5), fill=255)
    canvas.paste(badge_img, (bx, by), mask)
    text_centered(d, (bx, by, bx + bw, by + bh), "▸ コーチ向け", font(12, bold=True), WHITE)
    return y0 + mm(11)


def draw_hero(canvas, y0):
    d = ImageDraw.Draw(canvas)
    title_f = font(32, bold=True)
    d.text((PAD_X, y0), "コーチの仕事を、", font=title_f, fill=PURPLE_DARK)
    _, lh = measure_text(d, "コーチの仕事を、", title_f)
    y = y0 + lh + mm(1)
    d.text((PAD_X, y), "半分に。", font=title_f, fill=PURPLE_DARK)
    y += lh + mm(3)
    d.text((PAD_X, y), "指導者の準備時間と、指導の見落としをまるごと減らす。",
           font=font(11), fill=TEXT_DARK)
    y += mm(6)
    d.text((PAD_X, y), "30日無料トライアルで、コーチ機能をフル試用できます。",
           font=font(10), fill=TEXT_MUTED)
    return y + mm(7)


def draw_hero_feature(canvas, y0, num, title, desc, shot_path, points, color):
    """目玉機能大カード（圧縮版）"""
    d = ImageDraw.Draw(canvas)
    inner_w = mm(W_MM) - PAD_X * 2
    box_h = mm(52)
    rounded_rect(d, (PAD_X, y0, PAD_X + inner_w, y0 + box_h),
                 mm(3), fill=DARK_BG_2, outline=color, width=3)
    badge_w, badge_h = mm(26), mm(5.5)
    d.rounded_rectangle((PAD_X + mm(3), y0 + mm(2.5), PAD_X + mm(3) + badge_w, y0 + mm(2.5) + badge_h),
                        radius=mm(1.5), fill=color)
    text_centered(d, (PAD_X + mm(3), y0 + mm(2.5), PAD_X + mm(3) + badge_w, y0 + mm(2.5) + badge_h),
                  f"★ 目玉機能 #{num}", font(7.5, bold=True), WHITE)
    img_x0 = PAD_X + mm(3)
    img_y0 = y0 + mm(9.5)
    img_w = mm(80); img_h = mm(40)
    paste_screenshot(canvas, str(shot_path), (img_x0, img_y0, img_x0 + img_w, img_y0 + img_h),
                     radius_mm=2)
    tx = img_x0 + img_w + mm(4)
    ty = y0 + mm(9.5)
    d.text((tx, ty), title, font=font(11, bold=True), fill=WHITE)
    ty += mm(6)
    max_chars = 26
    lines = []
    cur = ""
    for ch in desc:
        cur += ch
        if len(cur) >= max_chars:
            lines.append(cur); cur = ""
    if cur: lines.append(cur)
    for ln in lines[:2]:
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
    """その他コーチ機能 4カード（2x2・圧縮版）"""
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ さらに、これだけの機能が使えます",
           font=font(10.5, bold=True), fill=DARK_TEXT)
    y = y0 + mm(5.5)
    inner_w = mm(W_MM) - PAD_X * 2
    col_w = (inner_w - mm(3)) // 2
    row_h = mm(17)
    items = [
        ("🎀", "コーチダッシュボード", "選手招待・QRコード・LINE共有をワンストップ", PURPLE),
        ("📋", "課題配布", "スキル＋トレを組み合わせて選手個別/全員に配信", PINK),
        ("🎬", "動画提出＋添削", "選手からの動画にテキストで返信・指導", CYAN),
        ("🔴", "新着提出 通知", "LINE風赤バッジで見落としゼロ", ORANGE),
    ]
    for i, (icon, title, body, color) in enumerate(items):
        col = i % 2
        row = i // 2
        cx0 = PAD_X + col * (col_w + mm(3))
        cy0 = y + row * (row_h + mm(2))
        rounded_rect(d, (cx0, cy0, cx0 + col_w, cy0 + row_h),
                     mm(2), fill=WHITE, outline=GRAY_BORDER, width=1)
        # 色サイド
        side_img = Image.new("RGB", (mm(3.5), row_h))
        gradient_rect(side_img, (0, 0, mm(3.5), row_h), color, color, "vertical")
        side_mask = Image.new("L", (mm(3.5), row_h), 0)
        ImageDraw.Draw(side_mask).rounded_rectangle((0, 0, mm(3.5), row_h), radius=mm(2), fill=255)
        canvas.paste(side_img, (cx0, cy0), side_mask)
        # 内容（絵文字は使わない、日本語のみ）
        d.text((cx0 + mm(5), cy0 + mm(2.2)), title, font=font(9.5, bold=True), fill=DARK_TEXT)
        d.text((cx0 + mm(5), cy0 + mm(8.5)), body, font=font(7), fill=TEXT_MUTED)
    return y + row_h * 2 + mm(2) + mm(4)


def draw_pricing(canvas, y0):
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ コーチ向けプラン",
           font=font(10.5, bold=True), fill=DARK_TEXT)
    y = y0 + mm(5.5)
    inner_w = mm(W_MM) - PAD_X * 2

    plans = [
        ("コーチ", "¥1,200/月", "〜10名の教室", PURPLE, False),
        ("コーチプラス", "¥1,980/月", "大規模チーム 無制限", PURPLE, False),
        ("トレーニング指導 NEW", "¥4,500/月", "個別メニュー + 添削20本", ORANGE, True),
        ("完全1on1 NEW", "¥7,500/月", "添削無制限 + 専用LINE", PINK, True),
    ]
    col_w = (inner_w - mm(3) * 3) // 4
    row_h = mm(18)
    for i, (name, price, desc, color, hi) in enumerate(plans):
        cx0 = PAD_X + i * (col_w + mm(3))
        cx1 = cx0 + col_w
        if hi:
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
            d.text((cx0 + mm(2), y + mm(1)), name, font=font(7.5, bold=True), fill=DARK_TEXT)
            d.text((cx0 + mm(2), y + mm(5)), price, font=font(11, bold=True), fill=color)
            d.text((cx0 + mm(2), y + mm(12)), desc, font=font(6), fill=TEXT_MUTED)
    y += row_h + mm(2)
    d.text((PAD_X, y), "※ フリー（¥0）・個人（¥480）でも動画閲覧・ロードマップ・トレメ作成は無料 ／ 新サブスクは先行受付中",
           font=font(6.5), fill=TEXT_MUTED)
    return y + mm(4)


def draw_footer(canvas, y0):
    d = ImageDraw.Draw(canvas)
    inner_w = mm(W_MM) - PAD_X * 2

    # CTA帯
    cta_h = mm(13)
    cta_img = Image.new("RGB", (inner_w, cta_h))
    gradient_rect(cta_img, (0, 0, inner_w, cta_h), PINK, PURPLE_DARK, "horizontal")
    mask = Image.new("L", (inner_w, cta_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, inner_w, cta_h), radius=mm(2.5), fill=255)
    canvas.paste(cta_img, (PAD_X, y0), mask)
    text_centered(d, (PAD_X, y0, PAD_X + inner_w, y0 + cta_h - mm(4)),
                  "▶ 30日 無料でコーチ機能をフル試用",
                  font(15, bold=True), WHITE)
    text_centered(d, (PAD_X, y0 + cta_h - mm(5), PAD_X + inner_w, y0 + cta_h),
                  "（クレジット登録なし・アカウント登録不要でも技リスト等の閲覧OK）",
                  font(8.5), (255, 235, 200))
    y = y0 + cta_h + mm(3)

    # QR + URL + 監修
    qr_size = mm(32)
    qr_path = OUT_DIR / "_promo_qr.png"
    gen_qr_png_hi("https://roadmap.cheer-tumbling.jp/", str(qr_path))
    draw_qr_box(canvas, (PAD_X, y, PAD_X + qr_size, y + qr_size), str(qr_path))
    # 右側
    tx = PAD_X + qr_size + mm(5)
    d.text((tx, y + mm(0.5)), "QRをスキャン or 直接アクセス", font=font(10, bold=True), fill=DARK_TEXT)
    d.text((tx, y + mm(6.5)), "roadmap.cheer-tumbling.jp", font=font(13, bold=True), fill=PURPLE_DARK)
    d.text((tx, y + mm(14)), "iPhone: Safari ／ Android: Chrome", font=font(7.5), fill=TEXT_MUTED)
    d.text((tx, y + mm(18)), "監修：中村 祐介（指導歴18年・元体操選手）", font=font(7), fill=TEXT_MUTED)
    d.text((tx, y + mm(22)), "　　　前島 一貴（国際ライセンス保有）", font=font(7), fill=TEXT_MUTED)
    d.text((tx, y + mm(26)), "発行：一般社団法人 チアタンブリング協会", font=font(6.5), fill=TEXT_MUTED)


def make_coach_flyer():
    img = make_canvas(W_MM, H_MM)
    y = mm(6)
    y = draw_header(img, y)
    y = draw_hero(img, y)

    y = draw_hero_feature(
        img, y, num=1,
        title="練習プログラム自動生成 → 指導配置図",
        desc="人数・指導者数・目標技を入れると、安全に回せるサーキット練習を自動設計。各ステーションへの指導者の配置も図示。",
        shot_path=SHOTS / "desktop" / "01_program_circuit.png",
        points=[
            "5ステーション設計、グループ人数も自動分配",
            "目標技ごとに「補助 / 自走 / 強化」を最適配置",
            "指導者1人で15名でも安全に回せる設計を支援",
        ],
        color=PURPLE,
    )
    y = draw_hero_feature(
        img, y, num=2,
        title="選手全員の進捗をヒートマップで一望",
        desc="達成率・習得済み・あと少しの技・練習中を色分け表示。次にどう伸ばすかの判断が瞬時にできます。",
        shot_path=SHOTS / "desktop" / "02_progress_heatmap.png",
        points=[
            "レベル別の到達率バーで「攻める技」が見える",
            "「あと少し」の可視化で指導の優先順位を整理",
            "選手ごとの成長タイムラインも閲覧可能",
        ],
        color=CYAN,
    )
    y = draw_other_features(img, y)
    y = draw_pricing(img, y)
    draw_footer(img, y)

    out_png = OUT_DIR / "【A4チラシ】コーチ向け.png"
    out_pdf = OUT_DIR / "【A4チラシ】コーチ向け.pdf"
    img.save(out_png, "PNG", dpi=(DPI, DPI))
    img.save(out_pdf, "PDF", resolution=DPI)
    print(f"✓ {out_png}")
    print(f"✓ {out_pdf}")


if __name__ == "__main__":
    make_coach_flyer()
