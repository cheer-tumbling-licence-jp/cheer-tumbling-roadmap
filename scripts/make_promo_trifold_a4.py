#!/usr/bin/env python3
"""
A4 三つ折り 総合版チラシ（新作、既存 A4 単ページ4種類と併存）

指定：
- A4 landscape（297mm × 210mm）を 99mm × 3 の巻き三つ折り
- A面（外側）3面 + B面（内側）3面 = 計6面
- 巻き三つ折り前提：右パネルが表紙、左パネルが内側に折り込まれる

A面（外側 = 折ったときに見える面）:
  左   [0-99mm]   ：料金プラン + 監修者 + 協会情報 + お問い合わせ
  中央 [99-198mm] ：裏表紙 = 数字バー + 完全無料 + 実績訴求
  右   [198-297mm]：表紙 = タイトル + キャッチ + メインビジュ + QR

B面（内側 = 開いたら3面連続で見える見開き）:
  左   [0-99mm]   ：コーチの価値
  中央 [99-198mm] ：選手の価値
  右   [198-297mm]：保護者の価値

出力：
- マーケティング/pdf/promo_trifold_a4_side_a_v1.pdf/png（A面・新2プラン目立ver）
- マーケティング/pdf/promo_trifold_a4_side_a_v4.pdf/png（A面・既存4プラン主役ver）
- マーケティング/pdf/promo_trifold_a4_side_b.pdf/png（B面・共通）
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
    gradient_rect, tri_gradient_rect, rounded_rect,
    text_centered, measure_text, make_canvas,
)
from make_promo_general_flyer import (
    font, gen_qr_png_hi, draw_qr_box, paste_screenshot,
    GREEN, BLUE, RED_NEW, GRAY_BORDER, DARK_TEXT,
)

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "マーケティング" / "pdf"
OUT_DIR.mkdir(exist_ok=True)
SHOTS = ROOT / "assets" / "lp-screenshots"

# === 三つ折り寸法 ===
SHEET_W_MM = 297   # A4 長辺（横）
SHEET_H_MM = 210   # A4 短辺（縦）
PANEL_W_MM = 99    # 各面の幅
PANEL_H_MM = 210   # 各面の高さ

# パネル境界の x（mm）
PANEL_X_MM = [0, 99, 198, 297]


# ===========================================================
# 共通ユーティリティ
# ===========================================================
def draw_fold_lines(canvas):
    """折り目のガイドライン（薄い破線）を印刷業者向けに入れる"""
    d = ImageDraw.Draw(canvas)
    for x_mm in [99, 198]:
        x = mm(x_mm)
        # 上下に短い破線を入れる（内容にはかぶらない）
        for y_mm in [0, SHEET_H_MM - 4]:
            for dy in range(0, mm(4), mm(0.8)):
                d.line([(x, mm(y_mm) + dy), (x, mm(y_mm) + dy + mm(0.4))],
                       fill=(200, 200, 200), width=1)


def paste_screenshot_contain(canvas, path, xy_box, bg_color=(20, 15, 40), radius_mm=1.5):
    """縦横比保持で枠内に完全に収める（余白は bg_color で塗る）。
    mobile の縦長スクショを cover fit すると読めなくなるため、この関数で全体を見せる。"""
    x0, y0, x1, y1 = xy_box
    w, h = x1 - x0, y1 - y0
    if not Path(path).exists():
        d = ImageDraw.Draw(canvas)
        rounded_rect(d, xy_box, mm(radius_mm), fill=(50, 35, 80), outline=(80, 60, 110), width=2)
        text_centered(d, xy_box, "[ App Screen ]", font(11, bold=True), (140, 130, 170))
        return
    img = Image.open(path).convert("RGB")
    scale = min(w / img.width, h / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    bg = Image.new("RGB", (w, h), bg_color)
    px = (w - nw) // 2
    py = (h - nh) // 2
    bg.paste(img, (px, py))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=mm(radius_mm), fill=255)
    canvas.paste(bg, (x0, y0), mask)


def paste_screenshot_slice(canvas, path, xy_box, y_start=0.05, y_end=0.35, radius_mm=1.5):
    """mobile 縦長スクショの縦スライス（意味のある領域）を抽出し、cover fit で枠を埋める。
    contain fit だと画像が小さく余白が大きくなるため、
    「上部から一定領域を抜き出して横長帯として見せる」方式で他パネルと同サイズに揃える。"""
    x0, y0, x1, y1 = xy_box
    w, h = x1 - x0, y1 - y0
    if not Path(path).exists():
        d = ImageDraw.Draw(canvas)
        rounded_rect(d, xy_box, mm(radius_mm), fill=(50, 35, 80), outline=(80, 60, 110), width=2)
        text_centered(d, xy_box, "[ App Screen ]", font(11, bold=True), (140, 130, 170))
        return
    img = Image.open(path).convert("RGB")
    top_px = int(img.height * y_start)
    bot_px = int(img.height * y_end)
    img = img.crop((0, top_px, img.width, bot_px))
    scale = max(w / img.width, h / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    cx0 = max(0, (nw - w) // 2)
    cy0 = max(0, (nh - h) // 2)
    img = img.crop((cx0, cy0, cx0 + w, cy0 + h))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=mm(radius_mm), fill=255)
    canvas.paste(img, (x0, y0), mask)


def wrap_text(text, max_chars):
    """max_chars 文字ごとに改行する簡易ラッパ"""
    lines, cur = [], ""
    for ch in text:
        cur += ch
        if ch == "\n":
            lines.append(cur.rstrip("\n"))
            cur = ""
        elif len(cur) >= max_chars:
            lines.append(cur)
            cur = ""
    if cur:
        lines.append(cur)
    return lines


def draw_bullet_list(d, x, y, items, char_font, line_h_mm=5.5, max_chars=22,
                     bullet="・", fill=TEXT_DARK, indent_mm=0):
    """・付きリスト。折り返し対応。"""
    for it in items:
        lines = wrap_text(it, max_chars)
        first = True
        for ln in lines:
            prefix = bullet if first else "　"
            d.text((x + mm(indent_mm), y), prefix + ln, font=char_font, fill=fill)
            y += mm(line_h_mm)
            first = False
        y += mm(0.5)
    return y


# ===========================================================
# A面 パネル①（右）：表紙
# ===========================================================
def draw_cover_panel(canvas, px0_mm, px1_mm):
    """
    表紙パネル 99mm × 210mm
    背景：紫→ピンクのフルグラデ
    上：協会名・業界初バッジ
    中：タイトル大 + キャッチ
    下：メインビジュ枠（スクショ）＋大きな QR
    """
    d = ImageDraw.Draw(canvas)
    x0, x1 = mm(px0_mm), mm(px1_mm)
    y0, y1 = 0, mm(PANEL_H_MM)
    W, H = x1 - x0, y1 - y0

    # フルパネルグラデ
    bg = Image.new("RGB", (W, H))
    tri_gradient_rect(bg, (0, 0, W, H), PURPLE_DARK, PINK, ORANGE, "diag")
    canvas.paste(bg, (x0, y0))

    inner_x = x0 + mm(7)
    inner_w = W - mm(14)

    # === 上部：協会名 ===
    y = mm(9)
    d.text((inner_x, y), "一般社団法人 チアタンブリング協会", font=font(7.5), fill=(255, 235, 240))
    d.text((inner_x, y + mm(4)), "公式アプリ", font=font(9, bold=True), fill=WHITE)

    # === 業界初！バッジ（右上に配置） ===
    bw, bh = mm(24), mm(8)
    bx = x1 - mm(7) - bw
    by = mm(9)
    badge = Image.new("RGB", (bw, bh))
    gradient_rect(badge, (0, 0, bw, bh), GOLD, ORANGE, "horizontal")
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), radius=mm(4), fill=255)
    canvas.paste(badge, (bx, by), mask)
    text_centered(d, (bx, by, bx + bw, by + bh), "業界初！", font(11, bold=True), (60, 30, 0))

    # === タイトル大 ===
    y = mm(28)
    title_f = font(19, bold=True)
    line_gap = mm(2.5)  # 行間を広めに取って視認性を上げる（旧 0.3mm → 2.5mm）
    d.text((inner_x, y), "正しい", font=title_f, fill=WHITE)
    _, lh = measure_text(d, "正しい", title_f)
    y += lh + line_gap
    d.text((inner_x, y), "タンブリングを、", font=title_f, fill=WHITE)
    y += lh + line_gap
    d.text((inner_x, y), "安全に、", font=title_f, fill=WHITE)
    y += lh + line_gap
    d.text((inner_x, y), "段階的に。", font=title_f, fill=GOLD)
    y += lh + mm(4)

    # キャッチ
    sub_f = font(9)
    d.text((inner_x, y), "指導者・選手・保護者のための、", font=sub_f, fill=(255, 235, 240))
    d.text((inner_x, y + mm(4.5)), "タンブリング教科書アプリ。", font=sub_f, fill=(255, 235, 240))

    # === メインビジュ（スクショ） ===
    shot = SHOTS / "mobile" / "01_home.png"
    if not shot.exists():
        # フォールバック候補
        for cand in [SHOTS / "desktop" / "01_program_circuit.png",
                     SHOTS / "desktop" / "02_progress_heatmap.png"]:
            if cand.exists():
                shot = cand
                break
    # 白フレーム背景
    fx0, fy0 = inner_x + mm(4), mm(87)
    fx1, fy1 = x1 - mm(11), mm(148)
    rounded_rect(d, (fx0 - mm(2), fy0 - mm(2), fx1 + mm(2), fy1 + mm(2)),
                 mm(3), fill=WHITE, outline=(255, 255, 255, 200), width=1)
    paste_screenshot(canvas, str(shot), (fx0, fy0, fx1, fy1), radius_mm=2)

    # === QR（下部・大きめ） ===
    qr_path = OUT_DIR / "_promo_qr.png"
    if not qr_path.exists():
        gen_qr_png_hi("https://roadmap.cheer-tumbling.jp/", str(qr_path))
    qr_size = mm(33)
    qx = inner_x
    qy = mm(157)
    # QR 白背景
    rounded_rect(d, (qx - mm(2), qy - mm(2), qx + qr_size + mm(2), qy + qr_size + mm(2)),
                 mm(2), fill=WHITE, outline=WHITE, width=1)
    qr = Image.open(qr_path).convert("RGB")
    qr = qr.resize((qr_size, qr_size), Image.LANCZOS)
    canvas.paste(qr, (qx, qy))

    # URL テキスト
    tx = qx + qr_size + mm(4)
    d.text((tx, qy + mm(3)), "QRから", font=font(8), fill=(255, 235, 240))
    d.text((tx, qy + mm(7.5)), "今すぐ", font=font(9.5, bold=True), fill=WHITE)
    d.text((tx, qy + mm(12)), "無料で", font=font(9.5, bold=True), fill=WHITE)
    d.text((tx, qy + mm(16.5)), "はじめる", font=font(9.5, bold=True), fill=GOLD)
    d.text((tx, qy + mm(24)), "登録不要", font=font(7, bold=True), fill=(255, 235, 240))
    d.text((tx, qy + mm(28)), "クレカ不要", font=font(7, bold=True), fill=(255, 235, 240))

    # 下部 URL 帯
    d.text((inner_x, mm(196)), "roadmap.cheer-tumbling.jp",
           font=font(10.5, bold=True), fill=WHITE)
    d.text((inner_x, mm(201.5)), "iPhone/Android/PC 対応",
           font=font(7), fill=(255, 235, 240))


# ===========================================================
# A面 パネル②（中央）：裏表紙 = 数字バー + 完全無料訴求
# ===========================================================
def draw_back_panel(canvas, px0_mm, px1_mm):
    """
    裏表紙パネル 99mm × 210mm
    上：見出し「ぜんぶ、無料で始められる。」
    中上：数字バー（33技・44トレ・105動画）
    中：完全無料メッセージ + 使える機能一覧
    下：実績・社会的証明・監修
    """
    d = ImageDraw.Draw(canvas)
    x0, x1 = mm(px0_mm), mm(px1_mm)
    y0, y1 = 0, mm(PANEL_H_MM)
    W = x1 - x0

    # 白背景
    d.rectangle((x0, y0, x1, y1), fill=(252, 250, 255))

    inner_x = x0 + mm(6)
    inner_w = W - mm(12)

    # === 見出し ===
    y = mm(12)
    d.text((inner_x, y), "■ アプリの中身", font=font(9, bold=True), fill=PURPLE_DARK)
    y += mm(6)
    hf = font(15, bold=True)
    d.text((inner_x, y), "ぜんぶ、", font=hf, fill=TEXT_DARK)
    _, lh = measure_text(d, "ぜんぶ、", hf)
    y += lh + mm(0.3)
    d.text((inner_x, y), "無料で始められる。", font=hf, fill=PURPLE_DARK)
    y += lh + mm(4)

    # === 数字バー（縦にコンパクトに） ===
    # 4番目のラベルは「段階別\nロードマップ」の2段組で枠内に収める
    stats = [
        ("33", ["技を体系化"]),
        ("44", ["トレーニング"]),
        ("105", ["解説動画"]),
        ("Lv1-6", ["段階別", "ロードマップ"]),
    ]
    bar_h = mm(22)
    bar_w = inner_w
    bar_img = Image.new("RGB", (bar_w, bar_h))
    gradient_rect(bar_img, (0, 0, bar_w, bar_h), PURPLE_DARK, PINK, "horizontal")
    mask = Image.new("L", (bar_w, bar_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bar_w, bar_h), radius=mm(3), fill=255)
    canvas.paste(bar_img, (inner_x, y), mask)
    seg_w = bar_w / 4
    for i, (num, label_lines) in enumerate(stats):
        sx0 = inner_x + int(i * seg_w)
        sx1 = inner_x + int((i + 1) * seg_w)
        num_f = font(15 if i < 3 else 9, bold=True)
        text_centered(d, (sx0, y + mm(2), sx1, y + mm(12)), num, num_f, WHITE)
        label_f = font(6.8)
        # ラベルを行ごとにセンタリング配置（1行または2行対応）
        n_lines = len(label_lines)
        label_area_top = y + mm(12)
        label_area_bot = y + bar_h - mm(1)
        line_slot = (label_area_bot - label_area_top) // max(n_lines, 1)
        for li, ln in enumerate(label_lines):
            top = label_area_top + li * line_slot
            bot = top + line_slot
            text_centered(d, (sx0, top, sx1, bot), ln, label_f, WHITE)
        if i > 0:
            d.line([(sx0, y + mm(3)), (sx0, y + bar_h - mm(3))], fill=(255, 255, 255), width=1)
    y += bar_h + mm(6)

    # === 完全無料 帯 ===
    free_h = mm(14)
    free_img = Image.new("RGB", (inner_w, free_h))
    gradient_rect(free_img, (0, 0, inner_w, free_h), GOLD, ORANGE, "horizontal")
    fm = Image.new("L", (inner_w, free_h), 0)
    ImageDraw.Draw(fm).rounded_rectangle((0, 0, inner_w, free_h), radius=mm(2.5), fill=255)
    canvas.paste(free_img, (inner_x, y), fm)
    # ラベル
    text_centered(d, (inner_x, y, inner_x + inner_w, y + free_h - mm(6)),
                  "◎ 完全無料でここまで使える！", font(11, bold=True), (60, 30, 0))
    text_centered(d, (inner_x, y + free_h - mm(6), inner_x + inner_w, y + free_h),
                  "アカウント登録なしでも今すぐ試せる", font(7.5), (60, 30, 0))
    y += free_h + mm(4)

    # === 無料で使える機能リスト ===
    free_features = [
        ("①", "解説動画 105 本すべて閲覧", "後方宙返りまで完全解説"),
        ("②", "オリジナル練習メニュー作成", "自分専用のセットを保存"),
        ("③", "成長記録 & ヒートマップ", "毎日の練習が可視化"),
        ("④", "Lv1〜Lv6 段階別ロードマップ", "次にやるべき技が分かる"),
    ]
    for icon, title, sub in free_features:
        # 左：番号丸（紫塗り＋白文字）
        cx = inner_x + mm(4)
        cy = y + mm(4)
        r = mm(3.5)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=PURPLE, outline=PURPLE_DARK, width=1)
        text_centered(d, (cx - r, cy - r, cx + r, cy + r), icon, font(11, bold=True), WHITE)
        # 本文
        tx = inner_x + mm(10)
        d.text((tx, y + mm(0.5)), title, font=font(8.8, bold=True), fill=TEXT_DARK)
        d.text((tx, y + mm(5)), sub, font=font(7), fill=TEXT_MUTED)
        y += mm(9)
    y += mm(3)

    # === 監修者ボックス ===
    sup_h = mm(24)
    rounded_rect(d, (inner_x, y, inner_x + inner_w, y + sup_h), mm(2),
                 fill=BG_CYAN_SOFT, outline=CYAN, width=1)
    d.text((inner_x + mm(3), y + mm(2)), "◆ 監修", font=font(7.5, bold=True), fill=CYAN)
    d.text((inner_x + mm(3), y + mm(7)),
           "中村 祐介（指導歴18年）", font=font(9, bold=True), fill=TEXT_DARK)
    d.text((inner_x + mm(3), y + mm(11.5)),
           "元体操選手・株式会社Gym plus 代表", font=font(6.5), fill=TEXT_MUTED)
    d.text((inner_x + mm(3), y + mm(15.5)),
           "前島 一貴（国際ライセンス）", font=font(9, bold=True), fill=TEXT_DARK)
    d.text((inner_x + mm(3), y + mm(20)),
           "元プロチアリーダー・協会代表理事", font=font(6.5), fill=TEXT_MUTED)
    y += sup_h + mm(3)

    # === フッター（このパネル用） ===
    y = mm(196)
    d.text((inner_x, y), "→ 詳しくはウラ面（3者別の特徴）へ",
           font=font(8, bold=True), fill=PURPLE_DARK)
    d.text((inner_x, y + mm(4.5)),
           "コーチ／選手／保護者、それぞれの活用ポイント",
           font=font(6.5), fill=TEXT_MUTED)


# ===========================================================
# A面 パネル③（左）：料金プラン + 監修者 + 協会情報
# ===========================================================
def draw_pricing_panel(canvas, px0_mm, px1_mm, variant="v1"):
    """
    variant:
      "v1": 新2プラン目立たせ ver（¥4,500/¥7,500 上に大きく、既存4プラン下に一覧）
      "v4": 既存4プラン主役 ver（フリー〜コーチプラス上に大きく、新2プラン下にサブ扱い）
    """
    d = ImageDraw.Draw(canvas)
    x0, x1 = mm(px0_mm), mm(px1_mm)
    W = x1 - x0

    # 淡グラデ背景
    bg = Image.new("RGB", (W, mm(PANEL_H_MM)))
    gradient_rect(bg, (0, 0, W, mm(PANEL_H_MM)), BG_PURPLE_SOFT, WHITE, "vertical")
    canvas.paste(bg, (x0, 0))

    inner_x = x0 + mm(6)
    inner_w = W - mm(12)

    # === 見出し ===
    y = mm(12)
    d.text((inner_x, y), "■ プラン一覧", font=font(9, bold=True), fill=PURPLE_DARK)
    y += mm(6)
    hf = font(13, bold=True)
    d.text((inner_x, y), "選べる", font=hf, fill=TEXT_DARK)
    _, lh = measure_text(d, "選べる", hf)
    y += lh + mm(0.3)
    d.text((inner_x, y), "6プラン。", font=hf, fill=PURPLE_DARK)
    y += lh + mm(5)

    if variant == "v1":
        y = _draw_pricing_v1_new_emphasis(canvas, d, inner_x, inner_w, y)
    else:  # v4
        y = _draw_pricing_v4_existing_emphasis(canvas, d, inner_x, inner_w, y)

    # === 協会情報・お問い合わせ ===
    y = mm(178)
    d.text((inner_x, y), "■ お問い合わせ", font=font(8, bold=True), fill=PURPLE_DARK)
    y += mm(5)
    d.text((inner_x, y), "一般社団法人 チアタンブリング協会",
           font=font(7.5, bold=True), fill=TEXT_DARK)
    y += mm(4)
    d.text((inner_x, y), "info@cheer-tumbling.jp", font=font(7.5), fill=TEXT_MUTED)
    y += mm(4)
    d.text((inner_x, y), "cheer-tumbling.jp", font=font(7.5), fill=TEXT_MUTED)


def _draw_pricing_v1_new_emphasis(canvas, d, inner_x, inner_w, y):
    """新2プラン目立たせ ver：上に新2プランを大きく、下に既存4プラン一覧"""
    # 【上段】新2プラン（縦並び、大きく）
    new_plans = [
        {
            "name": "トレーニング指導",
            "price": "¥4,500",
            "unit": "/月",
            "features": [
                "個別メニュー作成",
                "動画添削 月20本",
                "オンライン相談",
            ],
            "color_a": ORANGE,
            "color_b": ORANGE_DARK,
        },
        {
            "name": "完全 1on1",
            "price": "¥7,500",
            "unit": "/月",
            "features": [
                "動画添削 無制限",
                "専用 LINE サポート",
                "月1回オンライン通話",
            ],
            "color_a": PINK,
            "color_b": PURPLE_DARK,
        },
    ]
    for plan in new_plans:
        card_h = mm(30)
        card_img = Image.new("RGB", (inner_w, card_h))
        gradient_rect(card_img, (0, 0, inner_w, card_h), plan["color_a"], plan["color_b"], "diag")
        mask = Image.new("L", (inner_w, card_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, inner_w, card_h), radius=mm(2.5), fill=255)
        canvas.paste(card_img, (inner_x, y), mask)

        # NEW バッジ
        nb_w, nb_h = mm(11), mm(4.5)
        nb_x = inner_x + inner_w - nb_w - mm(2.5)
        nb_y = y + mm(2)
        d.rounded_rectangle((nb_x, nb_y, nb_x + nb_w, nb_y + nb_h), radius=mm(1.2), fill=WHITE)
        text_centered(d, (nb_x, nb_y, nb_x + nb_w, nb_y + nb_h),
                      "NEW", font(7, bold=True), plan["color_b"])
        # 名前
        d.text((inner_x + mm(3), y + mm(2)), plan["name"], font=font(10, bold=True), fill=WHITE)
        # 価格（大きく）
        pf = font(20, bold=True)
        d.text((inner_x + mm(3), y + mm(7.5)), plan["price"], font=pf, fill=WHITE)
        pw, _ = measure_text(d, plan["price"], pf)
        d.text((inner_x + mm(3) + pw + mm(1), y + mm(15)), plan["unit"],
               font=font(9), fill=WHITE)
        # feature 3件（右）
        fy = y + mm(2)
        for f in plan["features"]:
            d.text((inner_x + mm(50), fy), "・" + f, font=font(7), fill=WHITE)
            fy += mm(4)

        y += card_h + mm(3)

    # 準備中の注釈
    d.text((inner_x, y), "※ 新2プランは協会法人登記完了後に開始（先行受付中）",
           font=font(6), fill=TEXT_MUTED)
    y += mm(6)

    # 【下段】既存4プラン（コンパクトに横並び 2×2）
    d.text((inner_x, y), "▼ 既存プラン", font=font(7.5, bold=True), fill=TEXT_DARK)
    y += mm(4.5)

    existing = [
        ("フリー", "¥0", "動画105本 全部無料", (255, 200, 30)),
        ("個人", "¥480", "プレミアム動画解放", PURPLE),
        ("コーチ", "¥1,200", "教室主宰 〜10名", PURPLE_DARK),
        ("コーチ+", "¥1,980", "大規模チーム 無制限", PURPLE_DARK),
    ]
    ex_col_w = (inner_w - mm(2)) // 2
    ex_h = mm(13)
    for i, (name, price, desc, color) in enumerate(existing):
        col = i % 2
        row = i // 2
        cx0 = inner_x + col * (ex_col_w + mm(2))
        cy0 = y + row * (ex_h + mm(2))
        if i == 0:
            rounded_rect(d, (cx0, cy0, cx0 + ex_col_w, cy0 + ex_h), mm(1.5),
                         fill=(255, 250, 220), outline=(255, 200, 30), width=1)
            d.text((cx0 + mm(2), cy0 + mm(1)), name, font=font(7.5, bold=True), fill=(140, 100, 0))
            d.text((cx0 + mm(2), cy0 + mm(4.5)), price + "/月", font=font(9, bold=True), fill=(180, 130, 0))
            d.text((cx0 + mm(2), cy0 + mm(9)), desc, font=font(6), fill=(120, 90, 0))
        else:
            rounded_rect(d, (cx0, cy0, cx0 + ex_col_w, cy0 + ex_h), mm(1.5),
                         fill=WHITE, outline=BORDER, width=1)
            d.text((cx0 + mm(2), cy0 + mm(1)), name, font=font(7.5, bold=True), fill=TEXT_DARK)
            d.text((cx0 + mm(2), cy0 + mm(4.5)), price + "/月", font=font(9, bold=True), fill=color)
            d.text((cx0 + mm(2), cy0 + mm(9)), desc, font=font(6), fill=TEXT_MUTED)
    y += ex_h * 2 + mm(4)
    return y


def _draw_pricing_v4_existing_emphasis(canvas, d, inner_x, inner_w, y):
    """既存4プラン主役 ver：上に既存4プラン大きく縦並び、下に新2プランをサブで小さく"""
    # 【上段】既存4プラン（縦並び、大きく）
    existing = [
        {"name": "フリー", "price": "¥0/月", "desc": "解説動画105本すべて閲覧・トレメ作成・成長記録が全部無料",
         "highlight": True, "fill": (255, 250, 220), "border": (255, 200, 30), "price_c": (180, 130, 0)},
        {"name": "個人", "price": "¥480/月", "desc": "プレミアム動画解放・オンライン練習会参加",
         "highlight": False, "fill": WHITE, "border": BORDER, "price_c": PURPLE},
        {"name": "コーチ", "price": "¥1,200/月", "desc": "教室主宰向け・選手10名まで・課題配布と動画添削",
         "highlight": False, "fill": WHITE, "border": BORDER, "price_c": PURPLE_DARK},
        {"name": "コーチプラス", "price": "¥1,980/月", "desc": "大規模チーム向け・選手数無制限・副コーチ機能",
         "highlight": False, "fill": WHITE, "border": BORDER, "price_c": PURPLE_DARK},
    ]
    for plan in existing:
        card_h = mm(21)
        rounded_rect(d, (inner_x, y, inner_x + inner_w, y + card_h), mm(2),
                     fill=plan["fill"], outline=plan["border"],
                     width=2 if plan["highlight"] else 1)
        # 名前
        d.text((inner_x + mm(3), y + mm(2)), plan["name"],
               font=font(10, bold=True),
               fill=(140, 100, 0) if plan["highlight"] else TEXT_DARK)
        # 価格
        d.text((inner_x + mm(3), y + mm(7)), plan["price"],
               font=font(13, bold=True), fill=plan["price_c"])
        # 説明（折り返し）
        desc_lines = wrap_text(plan["desc"], 27)
        dy = y + mm(14)
        for ln in desc_lines[:2]:
            d.text((inner_x + mm(3), dy),
                   ln, font=font(6.8),
                   fill=(120, 90, 0) if plan["highlight"] else TEXT_MUTED)
            dy += mm(3)
        y += card_h + mm(2.5)

    y += mm(2)
    # 【下段】新2プランをサブで小さく
    d.text((inner_x, y), "▼ 準備中の新プラン（先行受付）",
           font=font(7.5, bold=True), fill=ORANGE_DARK)
    y += mm(4.5)

    new_plans = [
        ("トレーニング指導", "¥4,500/月", "個別メニュー・添削月20本", ORANGE, ORANGE_DARK),
        ("完全 1on1", "¥7,500/月", "添削無制限・専用LINE", PINK, PURPLE_DARK),
    ]
    for name, price, desc, ca, cb in new_plans:
        h = mm(11)
        bg = Image.new("RGB", (inner_w, h))
        gradient_rect(bg, (0, 0, inner_w, h), ca, cb, "horizontal")
        m = Image.new("L", (inner_w, h), 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, inner_w, h), radius=mm(1.5), fill=255)
        canvas.paste(bg, (inner_x, y), m)
        # 名前
        d.text((inner_x + mm(2.5), y + mm(0.7)), name, font=font(7.5, bold=True), fill=WHITE)
        # 価格
        d.text((inner_x + mm(2.5), y + mm(5)), price, font=font(9, bold=True), fill=WHITE)
        # 説明
        d.text((inner_x + mm(40), y + mm(1.5)), desc, font=font(6.5), fill=WHITE)
        # NEW バッジ
        nb_w, nb_h = mm(8), mm(3.5)
        nb_x = inner_x + inner_w - nb_w - mm(1.5)
        nb_y = y + mm(1)
        d.rounded_rectangle((nb_x, nb_y, nb_x + nb_w, nb_y + nb_h), radius=mm(0.8), fill=WHITE)
        text_centered(d, (nb_x, nb_y, nb_x + nb_w, nb_y + nb_h),
                      "NEW", font(6, bold=True), cb)
        y += h + mm(1.5)

    return y


# ===========================================================
# B面 パネル：3者別 詳細展開
# ===========================================================
def draw_role_panel(canvas, px0_mm, px1_mm, role_key):
    """
    3者別の詳細パネル 99mm × 210mm

    role_key: 'coach' | 'athlete' | 'parent'
    """
    d = ImageDraw.Draw(canvas)
    x0, x1 = mm(px0_mm), mm(px1_mm)
    y0, y1 = 0, mm(PANEL_H_MM)
    W = x1 - x0

    # 各パネルは 4 個の機能を持ち、番号丸 ①〜④ で表現
    # スクショを目玉機能の証拠として上部に配置するため 5→4 に削減
    CIRCLED = ["①", "②", "③", "④", "⑤"]
    ROLES = {
        "coach": {
            "role_label": "COACH",
            "title": "コーチへ",
            "sub": "教室主宰・部活顧問・専門コーチに",
            "color_main": PURPLE_DARK,
            "color_bg": (30, 20, 60),
            "color_accent": PURPLE,
            "headline": "指導と運営を、\n仕組みで支える。",
            "hero_shot": SHOTS / "desktop" / "01_program_circuit.png",
            "hero_caption": "→ 練習プログラム自動作成＋サーキット図",
            "features": [
                ("練習プログラム自動生成",
                 "人数・指導者・目標技を入れれば、\n安全に回せるサーキットが完成"),
                ("指導者の配置図まで自動",
                 "各ステーションに誰を配置するかを図示。\n初回でも即実施できる"),
                ("チームへ課題出題 & 動画添削",
                 "個別／全員へメニューを配布。\n提出動画にスタンプ＆コメントで返信"),
                ("選手全員の進捗をひと目で",
                 "誰がどの技まで到達したかを一覧。\n次に指導すべき点が見える"),
            ],
            "cta": "コーチプラン ¥1,200〜／月",
            "cta_sub": "無料で機能を試してから登録可",
        },
        "athlete": {
            "role_label": "ATHLETE",
            "title": "選手へ",
            "sub": "小学生〜社会人チアリーダーに",
            "color_main": CYAN,
            "color_bg": (10, 40, 55),
            "color_accent": (56, 189, 248),
            "headline": "自分のペースで、\n上達を可視化。",
            "hero_shot": SHOTS / "mobile" / "03_skill_detail.png",
            "hero_caption": "→ 技ごとに公式動画をタップで再生",
            "hero_fit": "slice",
            "hero_slice_y": (0.48, 0.78),  # 動画プレイヤーエリア（タップして再生ボタン）
            "features": [
                ("解説動画 105 本すべて閲覧",
                 "技ごとに動画・ポイント・注意点。\n後方宙返りまで完全解説"),
                ("トレーニング35種を回数付きで",
                 "各トレの目安回数・セットも表示。\nバリエーション動画も豊富"),
                ("チームコーチに課題を提出",
                 "動画をコーチへ送信して添削依頼。\nスタンプ＆コメント返信が届く"),
                ("成長記録ヒートマップ",
                 "毎日の練習が色で塗られる。\n連続日数・週の合計もひと目"),
            ],
            "cta": "フリープラン ¥0／月",
            "cta_sub": "登録なしでもすぐ試せる",
        },
        "parent": {
            "role_label": "PARENT",
            "title": "保護者へ",
            "sub": "お子様のチア・タンブリング上達を",
            "color_main": PINK,
            "color_bg": (55, 20, 45),
            "color_accent": (244, 114, 182),
            "headline": "見守れる、\nそして安心できる。",
            "hero_shot": SHOTS / "desktop" / "02_progress_heatmap.png",
            "hero_caption": "→ お子様の成長記録がアプリに残る",
            "features": [
                ("国際ライセンス保有者が監修",
                 "動画で「正しい技」の形とポイントを確認。\n体操専門家によるコンテンツ設計"),
                ("成長記録がアプリに保存される",
                 "できた技・練習日数・提出動画を\nまとめて確認できる"),
                ("安全性を第一に段階設計",
                 "無理な飛び級を防ぐ設計。\nケガのリスクを構造的に減らす"),
                ("コーチとの記録が残る",
                 "動画へのフィードバックが\nいつでも見返せる形で残る"),
            ],
            "cta": "動画閲覧・成長記録 ¥0",
            "cta_sub": "保護者アカウントは今後追加予定",
        },
    }

    r = ROLES[role_key]

    # === トップグラデ帯 ===
    top_h = mm(60)
    top_bg = Image.new("RGB", (W, top_h))
    gradient_rect(top_bg, (0, 0, W, top_h), r["color_bg"], r["color_main"], "diag")
    canvas.paste(top_bg, (x0, 0))
    # 白背景（残り）
    d.rectangle((x0, top_h, x1, y1), fill=(252, 250, 255))

    inner_x = x0 + mm(6)
    inner_w = W - mm(12)

    # === ヘッダ：役割ラベル + 対象 ===
    y = mm(11)
    # ロール英字ラベル（白実塗り＋メイン色文字）
    lb_w, lb_h = mm(22), mm(6.5)
    rounded_rect(d, (inner_x, y, inner_x + lb_w, y + lb_h), mm(1.5),
                 fill=WHITE, outline=WHITE, width=1)
    text_centered(d, (inner_x, y, inner_x + lb_w, y + lb_h),
                  r["role_label"], font(8, bold=True), r["color_main"])
    y += lb_h + mm(3)
    # 対象タイトル大
    d.text((inner_x, y), r["title"], font=font(17, bold=True), fill=WHITE)
    y += mm(11)
    d.text((inner_x, y), r["sub"], font=font(7.5), fill=(255, 245, 250))
    y += mm(6)

    # === ヘッドライン ===
    hf = font(14, bold=True)
    lines = r["headline"].split("\n")
    for ln in lines:
        d.text((inner_x, y), ln, font=hf, fill=WHITE)
        _, lh = measure_text(d, ln, hf)
        y += lh + mm(1)
    y += mm(4)

    # === 使用画面スクショ（ロールカラーの枠付き） ===
    shot_path = r.get("hero_shot")
    shot_y0, shot_y1 = mm(64), mm(99)
    if shot_path and Path(shot_path).exists():
        # 白フレーム＋ロールカラー枠
        frame_x0 = inner_x
        frame_x1 = inner_x + inner_w
        rounded_rect(d, (frame_x0 - mm(1), shot_y0 - mm(1),
                         frame_x1 + mm(1), shot_y1 + mm(1)),
                     mm(1.8), fill=WHITE, outline=r["color_main"], width=2)
        if r.get("hero_fit") == "slice":
            # mobile 縦長スクショから意味のあるスライスを抜き出して他パネルと同サイズに揃える
            y_s, y_e = r.get("hero_slice_y", (0.05, 0.35))
            paste_screenshot_slice(canvas, str(shot_path),
                                   (frame_x0, shot_y0, frame_x1, shot_y1),
                                   y_start=y_s, y_end=y_e, radius_mm=1.5)
        elif r.get("hero_fit") == "contain":
            paste_screenshot_contain(canvas, str(shot_path),
                                     (frame_x0, shot_y0, frame_x1, shot_y1),
                                     bg_color=r.get("hero_bg", (20, 15, 40)),
                                     radius_mm=1.5)
        else:
            paste_screenshot(canvas, str(shot_path),
                             (frame_x0, shot_y0, frame_x1, shot_y1), radius_mm=1.5)
        # キャプション（画面下のロールカラー小帯）
        cap = r.get("hero_caption") or ""
        if cap:
            cap_y = shot_y1 + mm(2)
            d.text((inner_x, cap_y), cap, font=font(7.5, bold=True), fill=r["color_main"])

    # === 特徴カード（4件、白背景で下に流す） ===
    y = mm(109)
    for idx, (title, desc) in enumerate(r["features"]):
        card_h = mm(19)
        # カード背景
        rounded_rect(d, (inner_x, y, inner_x + inner_w, y + card_h), mm(1.5),
                     fill=WHITE, outline=BORDER, width=1)
        # 左：番号丸（塗り＋アクセント枠 + 白文字大）
        cx = inner_x + mm(5)
        cy = y + mm(6)
        rr = mm(3.8)
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr),
                  fill=r["color_main"], outline=r["color_accent"], width=1)
        text_centered(d, (cx - rr, cy - rr, cx + rr, cy + rr),
                      CIRCLED[idx], font(12, bold=True), WHITE)
        # 本文
        tx = inner_x + mm(11)
        d.text((tx, y + mm(1.5)), title, font=font(8.3, bold=True), fill=TEXT_DARK)
        # 説明（改行対応）
        desc_lines = desc.split("\n")
        dy = y + mm(6.7)
        for dln in desc_lines[:2]:
            d.text((tx, dy), dln, font=font(6.5), fill=TEXT_MUTED)
            dy += mm(3.2)
        y += card_h + mm(1.5)

    # === CTA 帯（下部） ===
    y = mm(190)
    cta_h = mm(14)
    cta_img = Image.new("RGB", (inner_w, cta_h))
    gradient_rect(cta_img, (0, 0, inner_w, cta_h), r["color_main"], r["color_accent"], "horizontal")
    m = Image.new("L", (inner_w, cta_h), 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, inner_w, cta_h), radius=mm(2), fill=255)
    canvas.paste(cta_img, (inner_x, y), m)
    text_centered(d, (inner_x, y + mm(0.5), inner_x + inner_w, y + mm(7)),
                  r["cta"], font(10, bold=True), WHITE)
    text_centered(d, (inner_x, y + mm(7.5), inner_x + inner_w, y + cta_h),
                  r["cta_sub"], font(6.8), (255, 245, 250))


# ===========================================================
# ページ組み立て
# ===========================================================
def make_side_a(variant="v1"):
    """A面：左=料金プラン / 中央=裏表紙 / 右=表紙"""
    canvas = make_canvas(SHEET_W_MM, SHEET_H_MM)
    draw_pricing_panel(canvas, PANEL_X_MM[0], PANEL_X_MM[1], variant=variant)
    draw_back_panel(canvas, PANEL_X_MM[1], PANEL_X_MM[2])
    draw_cover_panel(canvas, PANEL_X_MM[2], PANEL_X_MM[3])
    draw_fold_lines(canvas)
    return canvas


def make_side_b():
    """B面（内側）：左=コーチ / 中央=選手 / 右=保護者"""
    canvas = make_canvas(SHEET_W_MM, SHEET_H_MM)
    draw_role_panel(canvas, PANEL_X_MM[0], PANEL_X_MM[1], "coach")
    draw_role_panel(canvas, PANEL_X_MM[1], PANEL_X_MM[2], "athlete")
    draw_role_panel(canvas, PANEL_X_MM[2], PANEL_X_MM[3], "parent")
    draw_fold_lines(canvas)
    return canvas


def save(canvas, base_name):
    png_path = OUT_DIR / f"{base_name}.png"
    pdf_path = OUT_DIR / f"{base_name}.pdf"
    canvas.save(png_path, "PNG", dpi=(DPI, DPI))
    canvas.save(pdf_path, "PDF", resolution=DPI)
    print(f"✓ {png_path}")
    print(f"✓ {pdf_path}")


def main():
    # A面 2バージョン
    save(make_side_a("v1"), "promo_trifold_a4_side_a_v1")
    save(make_side_a("v4"), "promo_trifold_a4_side_a_v4")
    # B面（共通）
    save(make_side_b(), "promo_trifold_a4_side_b")
    print("\n完了：全 6 ファイル出力（PDF 3 + PNG 3）")


if __name__ == "__main__":
    main()
