#!/usr/bin/env python3
"""
告知チラシ A4 総合版（3者別 + 目玉機能 + プラン詳細）
make_print_flyer.py のヘルパーを流用して、新指示（コーチ/保護者/選手別 + 新サブスク¥4,500/¥7,500）を反映。

出力：マーケティング/pdf/promo_general_a4.pdf
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

# 既存ヘルパーを import（font だけは日本語フォント用に上書き）
sys.path.insert(0, str(Path(__file__).parent))
from make_print_flyer import (
    DPI, mm,
    PURPLE, PURPLE_DARK, PINK, CYAN, GOLD,
    DARK_BG, DARK_BG_2, WHITE, TEXT_DIM, TEXT_MUTED, TEXT_DARK,
    BG_PURPLE_SOFT, BG_CYAN_SOFT, BORDER,
    ORANGE, ORANGE_DARK, ORANGE_LIGHT,
    gradient_rect, tri_gradient_rect, rounded_rect,
    text_centered, measure_text, make_canvas, draw_phone_mock,
)

# === 日本語フォント（ヒラギノ角ゴシック W3=Regular / W6=Bold） ===
FONT_JP_REG = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
FONT_JP_BLD = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"


def font(size_pt, bold=False):
    """日本語フォント。Hiragino Sans GB（中国語向け）の字形を回避。"""
    size_px = int(size_pt * DPI / 72)
    path = FONT_JP_BLD if bold else FONT_JP_REG
    return ImageFont.truetype(path, size_px)

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "マーケティング" / "pdf"
OUT_DIR.mkdir(exist_ok=True)
SHOTS = ROOT / "assets" / "lp-screenshots"

# 追加色
GREEN = (74, 222, 128)
BLUE = (96, 165, 250)
RED_NEW = (255, 75, 110)
GRAY_BORDER = (200, 195, 220)
DARK_TEXT = (45, 30, 70)

W_MM, H_MM = 210, 297
PAD_X = mm(10)


def draw_qr_box(canvas, xy_box, qr_path):
    x0, y0, x1, y1 = xy_box
    rounded_rect(ImageDraw.Draw(canvas), xy_box, mm(2), fill=WHITE, outline=GRAY_BORDER, width=2)
    if qr_path and Path(qr_path).exists():
        qr = Image.open(qr_path).convert("RGB")
        size = min(x1 - x0, y1 - y0) - mm(4)
        qr = qr.resize((size, size), Image.LANCZOS)
        canvas.paste(qr, (x0 + ((x1 - x0) - size) // 2, y0 + ((y1 - y0) - size) // 2))


def gen_qr_png(url, out_path, box_size=10):
    """qrcode が入っていれば QR を生成、無ければスキップ"""
    try:
        import qrcode
        img = qrcode.make(url, box_size=box_size, border=2)
        img.save(out_path)
        return True
    except Exception:
        return False


def gen_qr_png_hi(url, out_path):
    """印刷用 高品質 QR（誤り訂正 H・大ドット）"""
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_H
        qr = qrcode.QRCode(
            version=None,
            error_correction=ERROR_CORRECT_H,  # 30% 復元可能 = 印刷に強い
            box_size=24,
            border=2,
        )
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(out_path)
        return True
    except Exception:
        return False


def paste_screenshot(canvas, path, xy_box, radius_mm=2):
    """xy_box に screenshot を縦横比保持で貼り付け（角丸マスク付）"""
    x0, y0, x1, y1 = xy_box
    w, h = x1 - x0, y1 - y0
    if not Path(path).exists():
        # プレースホルダー
        d = ImageDraw.Draw(canvas)
        rounded_rect(d, xy_box, mm(radius_mm), fill=(50, 35, 80), outline=(80, 60, 110), width=2)
        text_centered(d, xy_box, "[ App Screen ]", font(11, bold=True), (140, 130, 170))
        return
    img = Image.open(path).convert("RGB")
    # 横比優先で縮小→中央クロップで枠ぴったり埋める
    scale = max(w / img.width, h / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    # 中央クロップ
    cx0 = (nw - w) // 2
    cy0 = (nh - h) // 2
    img = img.crop((cx0, cy0, cx0 + w, cy0 + h))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius=mm(radius_mm), fill=255)
    canvas.paste(img, (x0, y0), mask)


# ===========================================================
# 各セクション
# ===========================================================
def draw_header(canvas, y0):
    """① ヘッダー: 協会名（左） + 業界初！バッジ（右）"""
    d = ImageDraw.Draw(canvas)
    # 協会名（左）
    assoc_text = "一般社団法人 チアタンブリング協会  公式アプリ"
    f1 = font(8.5, bold=False)
    d.text((PAD_X, y0 + mm(2)), assoc_text, font=f1, fill=TEXT_MUTED)
    # 業界初！バッジ（右上）
    bw, bh = mm(22), mm(8)
    bx = mm(W_MM) - PAD_X - bw
    by = y0
    badge_img = Image.new("RGB", (bw, bh))
    gradient_rect(badge_img, (0, 0, bw, bh), RED_NEW, ORANGE, "horizontal")
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), radius=mm(4), fill=255)
    canvas.paste(badge_img, (bx, by), mask)
    text_centered(d, (bx, by, bx + bw, by + bh), "業界初！", font(12, bold=True), WHITE)
    return y0 + mm(11)


def draw_hero(canvas, y0):
    """② ヒーロー：タイトル + サブ + 数字バー"""
    d = ImageDraw.Draw(canvas)
    # タイトル2行（圧縮）
    title_f = font(24, bold=True)
    line1 = "正しいタンブリングを、"
    line2 = "安全に、段階的に。"
    d.text((PAD_X, y0), line1, font=title_f, fill=PURPLE_DARK)
    _, lh = measure_text(d, line1, title_f)
    y = y0 + lh + mm(0.5)
    d.text((PAD_X, y), line2, font=title_f, fill=PURPLE_DARK)
    y += lh + mm(1.5)
    sub_f = font(10)
    d.text((PAD_X, y), "指導者・選手・保護者のための、タンブリング教科書アプリ。", font=sub_f, fill=TEXT_DARK)
    y += mm(6)
    # 数字バー
    stats = [
        ("33", "技"),
        ("44", "トレーニング"),
        ("105", "解説動画"),
        ("Lv1〜Lv6", "段階別ロードマップ"),
    ]
    bar_h = mm(18)
    bar_y0, bar_y1 = y, y + bar_h
    bar_x0, bar_x1 = PAD_X, mm(W_MM) - PAD_X
    bar_w = bar_x1 - bar_x0
    bar_img = Image.new("RGB", (bar_w, bar_h))
    gradient_rect(bar_img, (0, 0, bar_w, bar_h), PURPLE_DARK, PINK, "horizontal")
    mask = Image.new("L", (bar_w, bar_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bar_w, bar_h), radius=mm(3), fill=255)
    canvas.paste(bar_img, (bar_x0, bar_y0), mask)
    seg_w = bar_w / 4
    for i, (num, label) in enumerate(stats):
        sx0 = bar_x0 + int(i * seg_w)
        sx1 = bar_x0 + int((i + 1) * seg_w)
        num_f = font(20 if i < 3 else 11, bold=True)
        text_centered(d, (sx0, bar_y0 + mm(2), sx1, bar_y0 + mm(11)), num, num_f, WHITE)
        label_f = font(8)
        text_centered(d, (sx0, bar_y0 + mm(11), sx1, bar_y1 - mm(1)), label, label_f, WHITE)
        # 仕切り線
        if i > 0:
            d.line([(sx0, bar_y0 + mm(3)), (sx0, bar_y1 - mm(3))], fill=(255, 255, 255, 80), width=1)
    y = bar_y1 + mm(3)
    # ▼ 無料アピール帯（基本機能は全部無料）
    free_h = mm(9)
    free_y0, free_y1 = y, y + free_h
    free_img = Image.new("RGB", (bar_w, free_h))
    gradient_rect(free_img, (0, 0, bar_w, free_h), (255, 235, 60), (255, 200, 30), "horizontal")
    fm = Image.new("L", (bar_w, free_h), 0)
    ImageDraw.Draw(fm).rounded_rectangle((0, 0, bar_w, free_h), radius=mm(2), fill=255)
    canvas.paste(free_img, (bar_x0, free_y0), fm)
    # アイコン枠（左）「無料」
    box_w = mm(20)
    d.rounded_rectangle((bar_x0 + mm(2), free_y0 + mm(1), bar_x0 + mm(2) + box_w, free_y1 - mm(1)),
                        radius=mm(1.5), fill=(45, 30, 70))
    text_centered(d, (bar_x0 + mm(2), free_y0, bar_x0 + mm(2) + box_w, free_y1),
                  "完全無料", font(11, bold=True), (255, 235, 60))
    # メッセージ
    d.text((bar_x0 + mm(2) + box_w + mm(4), free_y0 + mm(1)),
           "動画105本の閲覧／トレーニングメニュー作成／成長記録 すべて無料！",
           font=font(10, bold=True), fill=(45, 30, 70))
    d.text((bar_x0 + mm(2) + box_w + mm(4), free_y0 + mm(5.2)),
           "アカウント登録ナシでも、すぐに使えます。", font=font(7.5), fill=(80, 60, 110))
    return free_y1 + mm(4)


def draw_three_targets(canvas, y0):
    """③ 3者ストリップ（コーチ / 保護者 / 選手）"""
    d = ImageDraw.Draw(canvas)
    # 見出し
    h_f = font(11, bold=True)
    d.text((PAD_X, y0), "▸ 3者すべてに、効く。", font=h_f, fill=DARK_TEXT)
    y = y0 + mm(6)

    section_h = mm(34)
    inner_w = mm(W_MM) - PAD_X * 2
    col_w = (inner_w - mm(4)) // 3

    targets = [
        ("コーチ", "へ", PURPLE, [
            "練習プログラム自動生成",
            "指導配置を図で表示",
            "選手全員の進捗を一覧",
            "課題配布・動画添削",
        ]),
        ("保護者", "へ", PINK, [
            "お子様の上達がひと目",
            "安全と段階性を担保",
            "国際ライセンス監修",
            "成長記録の閲覧",
        ]),
        ("選手", "へ", CYAN, [
            "自分でメニュー作成",
            "成長記録ヒートマップ",
            "30日連続で動画解放",
            "Lv1〜Lv6 段階別構成",
        ]),
    ]
    for i, (audience, suffix, color, bullets) in enumerate(targets):
        cx0 = PAD_X + i * (col_w + mm(2))
        cx1 = cx0 + col_w
        cy0 = y
        cy1 = cy0 + section_h
        # カード背景（白＋色のサイドバー）
        rounded_rect(d, (cx0, cy0, cx1, cy1), mm(2), fill=WHITE, outline=GRAY_BORDER, width=1)
        # サイドバー（左 4mm の色帯）
        side_img = Image.new("RGB", (mm(4), section_h))
        gradient_rect(side_img, (0, 0, mm(4), section_h), color, color, "vertical")
        side_mask = Image.new("L", (mm(4), section_h), 0)
        ImageDraw.Draw(side_mask).rounded_rectangle((0, 0, mm(4), section_h), radius=mm(2), fill=255)
        canvas.paste(side_img, (cx0, cy0), side_mask)
        # 番号バッジ + タイトル
        num_str = ["①", "②", "③"][i]
        d.rounded_rectangle(
            (cx0 + mm(6), cy0 + mm(2.5), cx0 + mm(11), cy0 + mm(7.5)),
            radius=mm(1), fill=color,
        )
        text_centered(d, (cx0 + mm(6), cy0 + mm(2.5), cx0 + mm(11), cy0 + mm(7.5)),
                      num_str, font(9, bold=True), WHITE)
        d.text((cx0 + mm(13), cy0 + mm(2.8)),
               f"{audience}{suffix}", font=font(11, bold=True), fill=DARK_TEXT)
        # bullets
        by = cy0 + mm(11)
        for b in bullets:
            d.text((cx0 + mm(7), by), "・" + b, font=font(8.5), fill=TEXT_DARK)
            by += mm(5.5)
    return y + section_h + mm(5)


def draw_highlight(canvas, y0):
    """④ 目玉機能 2列（コーチ：プログラム配置図 / 選手：ヒートマップ）"""
    d = ImageDraw.Draw(canvas)
    # 見出し
    d.text((PAD_X, y0), "▸ 目玉機能", font=font(11, bold=True), fill=DARK_TEXT)
    y = y0 + mm(6)

    inner_w = mm(W_MM) - PAD_X * 2
    col_w = (inner_w - mm(4)) // 2
    sec_h = mm(60)

    items = [
        {
            "badge": "★コーチ",
            "title": "練習プログラム自動生成→指導配置図",
            "desc": "人数・指導者数・目標技を入れると、安全に回せるサーキット練習を自動設計。各ステーションへの指導者の配置も図示します。",
            "img": SHOTS / "desktop" / "01_program_circuit.png",
            "color": PURPLE,
        },
        {
            "badge": "★選手",
            "title": "成長記録ヒートマップ＋自主トレメ作成",
            "desc": "練習した日が色で塗られる。技ごとの達成率・あと少しの技も一目で。練習メニューは自分で組み立て、保存して繰り返せます。",
            "img": SHOTS / "desktop" / "02_progress_heatmap.png",
            "color": CYAN,
        },
    ]
    for i, item in enumerate(items):
        cx0 = PAD_X + i * (col_w + mm(4))
        cx1 = cx0 + col_w
        cy0 = y
        cy1 = cy0 + sec_h
        rounded_rect(d, (cx0, cy0, cx1, cy1), mm(2.5), fill=DARK_BG_2, outline=item["color"], width=2)
        # スクショ（大きく）
        img_h = mm(46)
        paste_screenshot(canvas, str(item["img"]),
                         (cx0 + mm(2), cy0 + mm(2), cx1 - mm(2), cy0 + mm(2) + img_h),
                         radius_mm=1.5)
        # バッジ
        ty = cy0 + mm(2) + img_h + mm(2)
        bw, _ = measure_text(d, item["badge"], font(8, bold=True))
        d.rounded_rectangle((cx0 + mm(3), ty, cx0 + mm(3) + bw + mm(4), ty + mm(5)),
                            radius=mm(1), fill=item["color"])
        d.text((cx0 + mm(5), ty + mm(0.7)), item["badge"], font=font(8, bold=True), fill=WHITE)
        ty += mm(7)
        # タイトル（折り返し対応せず短く）
        d.text((cx0 + mm(3), ty), item["title"], font=font(9.5, bold=True), fill=WHITE)
        ty += mm(5)
        # 説明（折り返し）
        words = item["desc"]
        max_chars = 26
        lines = []
        cur = ""
        for ch in words:
            cur += ch
            if len(cur) >= max_chars:
                lines.append(cur)
                cur = ""
        if cur:
            lines.append(cur)
        for ln in lines[:3]:
            d.text((cx0 + mm(3), ty), ln, font=font(7.5), fill=(220, 215, 240))
            ty += mm(3.6)
    return y + sec_h + mm(5)


def draw_pricing(canvas, y0):
    """⑤ プラン一覧（6プラン、新2つを目立たせる）"""
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ プラン", font=font(11, bold=True), fill=DARK_TEXT)
    y = y0 + mm(6)

    inner_w = mm(W_MM) - PAD_X * 2

    # 既存4プラン（小さく上段）
    existing = [
        ("フリー", "¥0/月", "動画105本＋トレメ＋記録、全部無料", (255, 200, 30)),
        ("個人", "¥480/月", "プレミアム動画も解放", PURPLE),
        ("コーチ", "¥1,200/月", "教室主宰（〜10名）", PURPLE),
        ("コーチプラス", "¥1,980/月", "大規模チーム(無制限)", PURPLE),
    ]
    ex_col_w = (inner_w - mm(3) * 3) // 4
    ex_h = mm(15)
    for i, (name, price, desc, color) in enumerate(existing):
        cx0 = PAD_X + i * (ex_col_w + mm(3))
        cx1 = cx0 + ex_col_w
        # フリー（i==0）は黄色背景で目立たせる
        if i == 0:
            rounded_rect(d, (cx0, y, cx1, y + ex_h), mm(1.5),
                         fill=(255, 248, 200), outline=(255, 200, 30), width=2)
            d.text((cx0 + mm(2), y + mm(1)), name, font=font(8, bold=True), fill=(140, 100, 0))
            d.text((cx0 + mm(2), y + mm(5)), price, font=font(11, bold=True), fill=(180, 130, 0))
            d.text((cx0 + mm(2), y + mm(10.5)), desc, font=font(6), fill=(120, 90, 0))
        else:
            rounded_rect(d, (cx0, y, cx1, y + ex_h), mm(1.5),
                         fill=BG_PURPLE_SOFT, outline=BORDER, width=1)
            d.text((cx0 + mm(2), y + mm(1)), name, font=font(7.5, bold=True), fill=DARK_TEXT)
            d.text((cx0 + mm(2), y + mm(5)), price, font=font(10, bold=True), fill=color)
            d.text((cx0 + mm(2), y + mm(10.5)), desc, font=font(6.5), fill=TEXT_MUTED)
    y += ex_h + mm(4)

    # 新サブスク2プラン（小さく・横長レイアウト）
    new_h = mm(16)
    new_w = (inner_w - mm(4)) // 2
    new_plans = [
        {
            "name": "トレーニング指導",
            "price": "¥4,500/月",
            "subtitle": "個別メニュー作成・動画添削月20本",
            "color_a": ORANGE,
            "color_b": ORANGE_DARK,
        },
        {
            "name": "完全1on1",
            "price": "¥7,500/月",
            "subtitle": "動画添削無制限・専用LINE・月1通話",
            "color_a": PINK,
            "color_b": PURPLE_DARK,
        },
    ]
    for i, plan in enumerate(new_plans):
        cx0 = PAD_X + i * (new_w + mm(4))
        cx1 = cx0 + new_w
        bg = Image.new("RGB", (new_w, new_h))
        gradient_rect(bg, (0, 0, new_w, new_h), plan["color_a"], plan["color_b"], "diag")
        mask = Image.new("L", (new_w, new_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, new_w, new_h), radius=mm(2), fill=255)
        canvas.paste(bg, (cx0, y), mask)
        # NEW バッジ
        nb_w, nb_h = mm(9), mm(4)
        nb_x = cx1 - nb_w - mm(2)
        nb_y = y + mm(1.5)
        d.rounded_rectangle((nb_x, nb_y, nb_x + nb_w, nb_y + nb_h), radius=mm(1), fill=WHITE)
        text_centered(d, (nb_x, nb_y, nb_x + nb_w, nb_y + nb_h), "NEW", font(6.5, bold=True), plan["color_b"])
        # 名前 + 価格（同じ行に並べる）
        d.text((cx0 + mm(2.5), y + mm(1.5)), plan["name"], font=font(9, bold=True), fill=WHITE)
        d.text((cx0 + mm(2.5), y + mm(6.5)), plan["price"], font=font(13, bold=True), fill=WHITE)
        # サブタイトル
        d.text((cx0 + mm(2.5), y + mm(12)), plan["subtitle"], font=font(6.8), fill=WHITE)
    y += new_h + mm(1)

    # 注釈
    d.text((PAD_X, y), "※ 新サブスク2種は先行受付中・準備中（協会法人登記完了後に開始）", font=font(7), fill=TEXT_MUTED)
    y += mm(5)
    return y


def draw_footer(canvas, y0):
    """⑥ フッター：QR + URL + 監修者 + CTA"""
    d = ImageDraw.Draw(canvas)
    inner_w = mm(W_MM) - PAD_X * 2

    # 横帯（CTA）
    cta_h = mm(13)
    cta_img = Image.new("RGB", (inner_w, cta_h))
    gradient_rect(cta_img, (0, 0, inner_w, cta_h), PINK, PURPLE_DARK, "horizontal")
    mask = Image.new("L", (inner_w, cta_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, inner_w, cta_h), radius=mm(2.5), fill=255)
    canvas.paste(cta_img, (PAD_X, y0), mask)
    text_centered(d, (PAD_X, y0, PAD_X + inner_w, y0 + cta_h - mm(4)),
                  "▶ 今すぐ無料で始める",
                  font(15, bold=True), WHITE)
    text_centered(d, (PAD_X, y0 + cta_h - mm(5), PAD_X + inner_w, y0 + cta_h),
                  "（動画閲覧・トレーニングメニュー作成・成長記録 まるごと無料）",
                  font(8.5), (255, 235, 200))
    y = y0 + cta_h + mm(3)

    # QR + URL + 監修（圧縮版：QR30mm + テキスト行間詰め）
    qr_size = mm(30)
    qr_path = OUT_DIR / "_promo_qr.png"
    gen_qr_png_hi("https://roadmap.cheer-tumbling.jp/", str(qr_path))
    draw_qr_box(canvas, (PAD_X, y, PAD_X + qr_size, y + qr_size), str(qr_path))

    tx = PAD_X + qr_size + mm(5)
    d.text((tx, y + mm(0)), "QRをスキャン or 直接アクセス", font=font(9.5, bold=True), fill=DARK_TEXT)
    d.text((tx, y + mm(5.5)), "roadmap.cheer-tumbling.jp", font=font(12.5, bold=True), fill=PURPLE_DARK)
    d.text((tx, y + mm(12)), "iPhone: Safari ／ Android: Chrome  ／  クレジット登録なし・無料", font=font(7), fill=TEXT_MUTED)
    d.text((tx, y + mm(16)), "監修：中村 祐介（指導歴18年）／ 前島 一貴（国際ライセンス保有）", font=font(7), fill=TEXT_MUTED)
    d.text((tx, y + mm(20)), "発行：一般社団法人 チアタンブリング協会", font=font(6.5), fill=TEXT_MUTED)


# ===========================================================
# main
# ===========================================================
def make_promo_general():
    img = make_canvas(W_MM, H_MM)
    y = mm(6)
    y = draw_header(img, y)
    y = draw_hero(img, y)
    y = draw_three_targets(img, y)
    y = draw_highlight(img, y)
    y = draw_pricing(img, y)
    draw_footer(img, y)

    out_png = OUT_DIR / "promo_general_a4.png"
    out_pdf = OUT_DIR / "promo_general_a4.pdf"
    img.save(out_png, "PNG", dpi=(DPI, DPI))
    img.save(out_pdf, "PDF", resolution=DPI)
    print(f"✓ {out_png}")
    print(f"✓ {out_pdf}")


if __name__ == "__main__":
    make_promo_general()
