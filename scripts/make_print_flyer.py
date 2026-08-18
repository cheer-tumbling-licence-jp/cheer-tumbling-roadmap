#!/usr/bin/env python3
"""
A4チラシ・A3ポスターを Pillow で 300DPI で直接生成する。
HTML→PDF の不確実性を完全に排除し、ピクセル単位で正確な印刷物を作る。

出力：
- マーケティング/pdf/flyer_a4_print.pdf (A4 印刷用 PDF、300DPI)
- マーケティング/pdf/poster_a3_print.pdf (A3 印刷用 PDF、300DPI)
- ~/Desktop/タンブリングロードマップ_配布物_YYYYMMDD/ にもコピー
"""
import os
from datetime import datetime
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "マーケティング" / "pdf"
OUT_DIR.mkdir(exist_ok=True)

# === 定数 ===
DPI = 300
MM_TO_PX = DPI / 25.4  # 約 11.81 px/mm

def mm(v):
    return int(v * MM_TO_PX)

# === 色（HTML版と整合） ===
PURPLE = (139, 92, 246)
PURPLE_DARK = (109, 40, 217)
PINK = (236, 72, 153)
CYAN = (6, 182, 212)
GOLD = (255, 210, 63)
DARK_BG = (42, 27, 78)
DARK_BG_2 = (22, 13, 40)
TEXT_DARK = (31, 20, 56)
TEXT_DIM = (107, 99, 134)
TEXT_MUTED = (74, 59, 106)
WHITE = (255, 255, 255)
BG_PURPLE_SOFT = (250, 245, 255)
BG_CYAN_SOFT = (240, 249, 255)
BORDER = (233, 228, 245)
ORANGE_LIGHT = (255, 247, 237)
ORANGE = (251, 146, 60)
ORANGE_DARK = (194, 65, 12)

# === フォントパス（Hiragino Sans GB は TTC で W3/W6 含む） ===
FONT_PATH = "/System/Library/Fonts/Hiragino Sans GB.ttc"

def font(size_pt, bold=False):
    """指定 pt のフォント（300DPI 換算で px へ変換）"""
    size_px = int(size_pt * DPI / 72)
    return ImageFont.truetype(FONT_PATH, size_px, index=1 if bold else 0)


def gradient_rect(img, xy, color_start, color_end, direction="diag"):
    """グラデーション矩形を img に描画"""
    x0, y0, x1, y1 = xy
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return
    grad = Image.new("RGB", (w, h))
    pixels = grad.load()
    for j in range(h):
        for i in range(w):
            if direction == "horizontal":
                t = i / max(w - 1, 1)
            elif direction == "vertical":
                t = j / max(h - 1, 1)
            else:  # diagonal 135 度
                t = (i + j) / max(w + h - 2, 1)
            r = int(color_start[0] + (color_end[0] - color_start[0]) * t)
            g = int(color_start[1] + (color_end[1] - color_start[1]) * t)
            b = int(color_start[2] + (color_end[2] - color_start[2]) * t)
            pixels[i, j] = (r, g, b)
    img.paste(grad, (x0, y0))


def tri_gradient_rect(img, xy, c1, c2, c3, direction="diag"):
    """3色グラデーション"""
    x0, y0, x1, y1 = xy
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        return
    grad = Image.new("RGB", (w, h))
    pixels = grad.load()
    for j in range(h):
        for i in range(w):
            if direction == "horizontal":
                t = i / max(w - 1, 1)
            elif direction == "vertical":
                t = j / max(h - 1, 1)
            else:
                t = (i + j) / max(w + h - 2, 1)
            if t < 0.5:
                u = t * 2
                r = int(c1[0] + (c2[0] - c1[0]) * u)
                g = int(c1[1] + (c2[1] - c1[1]) * u)
                b = int(c1[2] + (c2[2] - c1[2]) * u)
            else:
                u = (t - 0.5) * 2
                r = int(c2[0] + (c3[0] - c2[0]) * u)
                g = int(c2[1] + (c3[1] - c2[1]) * u)
                b = int(c2[2] + (c3[2] - c2[2]) * u)
            pixels[i, j] = (r, g, b)
    img.paste(grad, (x0, y0))


def rounded_rect(draw, xy, radius, fill, outline=None, width=1):
    """角丸矩形（PIL の rounded_rectangle を使用）"""
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def text_centered(draw, xy_box, text, font_obj, fill):
    """ボックスの中央にテキストを描く"""
    x0, y0, x1, y1 = xy_box
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = x0 + ((x1 - x0) - tw) / 2 - bbox[0]
    ty = y0 + ((y1 - y0) - th) / 2 - bbox[1]
    draw.text((tx, ty), text, font=font_obj, fill=fill)


def measure_text(draw, text, font_obj):
    bbox = draw.textbbox((0, 0), text, font=font_obj)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def make_canvas(width_mm, height_mm):
    """印刷用キャンバスを背景グラデーション付きで作成"""
    w = mm(width_mm)
    h = mm(height_mm)
    img = Image.new("RGB", (w, h), WHITE)
    # 縦方向のソフトグラデーション
    pixels = img.load()
    for y in range(h):
        t = y / max(h - 1, 1)
        if t < 0.5:
            u = t * 2
            r = int(255 + (250 - 255) * u)
            g = int(255 + (245 - 255) * u)
            b = int(255 + (255 - 255) * u)
        else:
            u = (t - 0.5) * 2
            r = int(250 + (240 - 250) * u)
            g = int(245 + (249 - 245) * u)
            b = int(255 + (255 - 255) * u)
        for x in range(w):
            pixels[x, y] = (r, g, b)
    return img


def draw_phone_mock(canvas, screenshot_path, xy_box):
    """xy_box の領域に iPad mockup（暗背景 + 内側画像）を描画"""
    x0, y0, x1, y1 = xy_box
    w, h = x1 - x0, y1 - y0

    # 暗いグラデ枠
    frame = Image.new("RGB", (w, h))
    pixels = frame.load()
    for j in range(h):
        for i in range(w):
            t = (i + j) / max(w + h - 2, 1)
            r = int(DARK_BG[0] + (DARK_BG_2[0] - DARK_BG[0]) * t)
            g = int(DARK_BG[1] + (DARK_BG_2[1] - DARK_BG[1]) * t)
            b = int(DARK_BG[2] + (DARK_BG_2[2] - DARK_BG[2]) * t)
            pixels[i, j] = (r, g, b)

    # 角丸マスク
    mask = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle((0, 0, w, h), radius=mm(5), fill=255)
    canvas.paste(frame, (x0, y0), mask)

    # スクリーンショット
    if screenshot_path and Path(screenshot_path).exists():
        pad_top = mm(7)
        pad_side = mm(3)
        pad_bot = mm(3)
        ss_w = w - pad_side * 2
        ss_h_max = h - pad_top - pad_bot

        ss = Image.open(screenshot_path).convert("RGB")
        # アスペクト比保持してフィット
        ss_w_target = ss_w
        ss_h_target = int(ss.height * ss_w_target / ss.width)
        if ss_h_target > ss_h_max:
            ss_h_target = ss_h_max
            ss_w_target = int(ss.width * ss_h_target / ss.height)
        ss = ss.resize((ss_w_target, ss_h_target), Image.LANCZOS)

        # 角丸マスクで貼り付け
        ss_mask = Image.new("L", (ss_w_target, ss_h_target), 0)
        ImageDraw.Draw(ss_mask).rounded_rectangle(
            (0, 0, ss_w_target, ss_h_target), radius=mm(2), fill=255
        )
        ss_x = x0 + (w - ss_w_target) // 2
        ss_y = y0 + pad_top
        canvas.paste(ss, (ss_x, ss_y), ss_mask)

    # トップノッチ（小さな黒い棒）
    notch_w = mm(15)
    notch_h = mm(1.2)
    notch_x = x0 + (w - notch_w) // 2
    notch_y = y0 + mm(2.5)
    nd = ImageDraw.Draw(canvas)
    nd.rounded_rectangle(
        (notch_x, notch_y, notch_x + notch_w, notch_y + notch_h),
        radius=mm(0.6), fill=(85, 85, 85)
    )


# ===========================================================
# A4 チラシ
# ===========================================================
def make_flyer_a4():
    W_MM, H_MM = 210, 297
    img = make_canvas(W_MM, H_MM)
    draw = ImageDraw.Draw(img)

    PAD_X = mm(12)
    INNER_W = mm(W_MM) - PAD_X * 2
    y = mm(10)

    # === バッジ ===
    badge_text = "一般社団法人 チアタンブリング協会 公式"
    badge_font = font(10, bold=True)
    bw, bh = measure_text(draw, badge_text, badge_font)
    bx0, by0 = PAD_X, y
    bx1, by1 = bx0 + bw + mm(10), by0 + bh + mm(3)
    # グラデバッジ
    badge_img = Image.new("RGB", (bx1-bx0, by1-by0))
    gradient_rect(badge_img, (0, 0, bx1-bx0, by1-by0), PINK, PURPLE, "diag")
    mask = Image.new("L", (bx1-bx0, by1-by0), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,bx1-bx0,by1-by0), radius=mm(2.5), fill=255)
    img.paste(badge_img, (bx0, by0), mask)
    draw.text((bx0 + mm(5), by0 + mm(1.5)), badge_text, font=badge_font, fill=WHITE)
    y = by1 + mm(5)

    # === タイトル ===
    title_lines = ["正しいタンブリングを、", "安全に、段階的に。"]
    title_font = font(36, bold=True)
    for line in title_lines:
        draw.text((PAD_X, y), line, font=title_font, fill=PURPLE)
        _, lh = measure_text(draw, line, title_font)
        y += lh + mm(0.5)
    y += mm(3)

    # === サブタイトル ===
    subtitle = "指導者・選手のためのタンブリング練習ロードマップアプリ"
    sub_font = font(12, bold=True)
    draw.text((PAD_X, y), subtitle, font=sub_font, fill=TEXT_MUTED)
    _, sh = measure_text(draw, subtitle, sub_font)
    y += sh + mm(5)

    # === 本文 + iPad mockup を 2 列 ===
    image_col_w = mm(62)
    image_col_h = mm(90)
    text_col_w = INNER_W - image_col_w - mm(6)

    # iPad mockup（右列）
    mock_x0 = PAD_X + text_col_w + mm(6)
    mock_y0 = y
    mock_x1 = mock_x0 + image_col_w
    mock_y1 = mock_y0 + image_col_h
    draw_phone_mock(img, str(ROOT / "マーケティング" / "screenshots" / "app-main.png"),
                    (mock_x0, mock_y0, mock_x1, mock_y1))
    # キャプション
    cap = "↑ 実際のアプリ画面"
    cap_font = font(9, bold=True)
    cw, ch = measure_text(draw, cap, cap_font)
    draw.text((mock_x0 + (image_col_w - cw)//2, mock_y1 + mm(2.5)),
              cap, font=cap_font, fill=TEXT_MUTED)

    # 本文（左列）— text_col_w 幅いっぱいに自動折り返し
    lead_text = (
        "指導歴18年の元体操選手が監修した、"
        "チア・体操指導者と選手のための学習アプリ。"
        "ウォームアップから後方宙返りまでの主要技を、"
        "習得順に並べたロードマップで体系化。"
        "動画解説・前段階の必須スキル・つまずきポイント・"
        "推奨トレーニングをすべて一画面で確認できます。"
    )
    lead_font = font(12)
    line_y = y
    current_line = ""
    for ch in lead_text:
        test = current_line + ch
        tw, _ = measure_text(draw, test, lead_font)
        if tw > text_col_w and current_line:
            draw.text((PAD_X, line_y), current_line, font=lead_font, fill=TEXT_DARK)
            _, lh = measure_text(draw, current_line, lead_font)
            line_y += lh + mm(1.2)
            current_line = ch
        else:
            current_line = test
    if current_line:
        draw.text((PAD_X, line_y), current_line, font=lead_font, fill=TEXT_DARK)
        _, lh = measure_text(draw, current_line, lead_font)
        line_y += lh + mm(7)

    # 左列にハイライトポイント（チェック付き）で下の余白を埋める
    highlights = [
        ("レベル順・系譜図で体系化", "技の習得順序が一目で分かる"),
        ("動画付き解説 60本以上", "観察ポイント・つまずき要因も網羅"),
        ("コーチと選手の連携機能", "課題配布・動画提出・進捗の自動共有"),
    ]
    hl_title_font = font(12, bold=True)
    hl_desc_font = font(10)
    # チェックアイコンサイズ
    chk_size = mm(6)
    for title, desc in highlights:
        # チェック丸（紫グラデ）
        chk_x = PAD_X
        chk_y = line_y + mm(0.5)
        draw.ellipse((chk_x, chk_y, chk_x + chk_size, chk_y + chk_size), fill=PURPLE)
        # チェックマーク（白で✓的に2本線）
        cx_a = chk_x + mm(1.4)
        cy_a = chk_y + mm(3.1)
        cx_b = chk_x + mm(2.6)
        cy_b = chk_y + mm(4.3)
        cx_c = chk_x + mm(4.6)
        cy_c = chk_y + mm(1.7)
        draw.line([(cx_a, cy_a), (cx_b, cy_b)], fill=WHITE, width=mm(0.6))
        draw.line([(cx_b, cy_b), (cx_c, cy_c)], fill=WHITE, width=mm(0.6))
        # テキスト
        text_x = chk_x + chk_size + mm(3)
        draw.text((text_x, line_y), title, font=hl_title_font, fill=TEXT_DARK)
        _, tlh = measure_text(draw, title, hl_title_font)
        draw.text((text_x, line_y + tlh + mm(0.5)), desc, font=hl_desc_font, fill=TEXT_DIM)
        _, dlh = measure_text(draw, desc, hl_desc_font)
        line_y += tlh + mm(0.5) + dlh + mm(4)

    y = mock_y1 + mm(8)

    # === 数字カード（4個） ===
    stats = [("33", "技"), ("44", "トレ"), ("60+", "動画"), ("30", "日 無料")]
    stat_box_h = mm(20)
    stat_card_x0 = PAD_X
    stat_card_x1 = PAD_X + INNER_W
    rounded_rect(draw, (stat_card_x0, y, stat_card_x1, y + stat_box_h),
                 radius=mm(3), fill=WHITE, outline=BORDER, width=2)
    stat_w = INNER_W // 4
    num_font = font(26, bold=True)
    lbl_font = font(9, bold=True)
    for i, (num, lbl) in enumerate(stats):
        cx0 = stat_card_x0 + i * stat_w
        cx1 = cx0 + stat_w
        text_centered(draw, (cx0, y + mm(2), cx1, y + mm(13)), num, num_font, PURPLE)
        text_centered(draw, (cx0, y + mm(13), cx1, y + stat_box_h - mm(2)), lbl, lbl_font, TEXT_MUTED)
    y += stat_box_h + mm(5)

    # === 機能カード 2x2 ===
    features = [
        ("📚", "技ロードマップ閲覧", "33技+44トレを動画付き／レベル順／系譜図で閲覧"),
        ("📋", "練習メニュー作成", "技とトレを組合せて自分用に保存、共有も可能"),
        ("📈", "選手ごとの進捗記録", "「習得中／合格」を技ごとに記録、俯瞰で把握"),
        ("⚙️", "練習プログラム自動生成", "人数・時間・目標からWU→補強→技練習を提案"),
    ]
    card_gap = mm(3)
    card_w = (INNER_W - card_gap) // 2
    card_h = mm(22)
    for i, (icon, title, desc) in enumerate(features):
        row = i // 2
        col = i % 2
        cx0 = PAD_X + col * (card_w + card_gap)
        cy0 = y + row * (card_h + card_gap)
        cx1 = cx0 + card_w
        cy1 = cy0 + card_h
        # カード白背景
        rounded_rect(draw, (cx0, cy0, cx1, cy1), radius=mm(2.5), fill=WHITE,
                     outline=BORDER, width=1)
        # 左の紫ボーダー
        draw.rectangle((cx0, cy0, cx0 + mm(1), cy1), fill=PURPLE)
        # タイトル
        tfont = font(11, bold=True)
        draw.text((cx0 + mm(5), cy0 + mm(3.5)), title, font=tfont, fill=TEXT_DARK)
        # 説明
        dfont = font(8.5)
        # 折り返し
        words = desc
        line_y2 = cy0 + mm(10)
        # 描画範囲：card width - 左borderと左右padding
        max_w = card_w - mm(8)
        # シンプル：自動折り返し
        current_line = ""
        for ch in words:
            test = current_line + ch
            tw, _ = measure_text(draw, test, dfont)
            if tw > max_w and current_line:
                draw.text((cx0 + mm(5), line_y2), current_line, font=dfont, fill=TEXT_DIM)
                _, tlh = measure_text(draw, current_line, dfont)
                line_y2 += tlh + mm(0.4)
                current_line = ch
            else:
                current_line = test
        if current_line:
            draw.text((cx0 + mm(5), line_y2), current_line, font=dfont, fill=TEXT_DIM)

    y += card_h * 2 + card_gap + mm(5)

    # === 利用シーン（1行のタグ） ===
    uc_label = "こんな現場で使えます："
    tags = ["チア指導者", "体操教室", "バク転教室", "アクロバット", "保護者", "部活顧問"]
    uc_label_font = font(9, bold=True)
    tag_font = font(8.5, bold=True)
    cur_x = PAD_X
    draw.text((cur_x, y + mm(1.5)), uc_label, font=uc_label_font, fill=TEXT_DIM)
    lw, _ = measure_text(draw, uc_label, uc_label_font)
    cur_x += lw + mm(2)
    for t in tags:
        tw, th = measure_text(draw, t, tag_font)
        tx0 = cur_x
        tx1 = tx0 + tw + mm(6)
        ty0 = y
        ty1 = y + th + mm(2.5)
        rounded_rect(draw, (tx0, ty0, tx1, ty1), radius=mm(5),
                     fill=WHITE, outline=(196, 181, 253), width=1)
        draw.text((tx0 + mm(3), ty0 + mm(1.2)), t, font=tag_font, fill=PURPLE_DARK)
        cur_x = tx1 + mm(1.5)
    y += mm(10)

    # === QR セクション ===
    qr_x0 = PAD_X
    qr_x1 = PAD_X + INNER_W
    qr_h = mm(50)
    qr_y0 = y
    qr_y1 = y + qr_h
    # 3色グラデの背景
    grad_box = Image.new("RGB", (INNER_W, qr_h))
    tri_gradient_rect(grad_box, (0, 0, INNER_W, qr_h), PINK, PURPLE, CYAN, "horizontal")
    qr_mask = Image.new("L", (INNER_W, qr_h), 0)
    ImageDraw.Draw(qr_mask).rounded_rectangle((0, 0, INNER_W, qr_h), radius=mm(3), fill=255)
    img.paste(grad_box, (qr_x0, qr_y0), qr_mask)

    # 上部見出し
    heading = "今すぐ 30 日無料で始められます"
    hd_font = font(14, bold=True)
    hw, hh = measure_text(draw, heading, hd_font)
    draw.text((qr_x0 + (INNER_W - hw)//2, qr_y0 + mm(3)), heading, font=hd_font, fill=WHITE)
    sub_qr = "クレジットカード不要・1分で開始"
    sub_qr_font = font(9.5)
    sw, _ = measure_text(draw, sub_qr, sub_qr_font)
    draw.text((qr_x0 + (INNER_W - sw)//2, qr_y0 + mm(10.5)), sub_qr, font=sub_qr_font, fill=WHITE)

    # 内側の白カード（QR + テキスト）
    inner_x0 = qr_x0 + mm(4)
    inner_x1 = qr_x1 - mm(4)
    inner_y0 = qr_y0 + mm(17)
    inner_y1 = qr_y1 - mm(4)
    rounded_rect(draw, (inner_x0, inner_y0, inner_x1, inner_y1), radius=mm(2.5), fill=WHITE)

    # QR画像
    qr_size = mm(26)
    qr_path = ROOT / "マーケティング" / "qr_share.png"
    if qr_path.exists():
        qr_img = Image.open(qr_path).convert("RGB")
        qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
        img.paste(qr_img, (inner_x0 + mm(3), inner_y0 + mm(2)))

    # テキスト右側
    info_x = inner_x0 + qr_size + mm(8)
    info_y = inner_y0 + mm(3)
    scan_font = font(9.5, bold=True)
    draw.text((info_x, info_y), "QRスキャンまたは下記URLへ", font=scan_font, fill=TEXT_DARK)
    info_y += mm(5)
    url_font = font(9)
    draw.text((info_x, info_y), "roadmap.cheer-tumbling.jp/", font=url_font, fill=TEXT_MUTED)
    info_y += mm(5)
    # 警告ボックス
    warn_x0 = info_x
    warn_x1 = inner_x1 - mm(3)
    warn_y0 = info_y
    warn_y1 = warn_y0 + mm(11)
    rounded_rect(draw, (warn_x0, warn_y0, warn_x1, warn_y1), radius=mm(1.5),
                 fill=ORANGE_LIGHT, outline=ORANGE, width=1)
    warn_font = font(8, bold=True)
    draw.text((warn_x0 + mm(2), warn_y0 + mm(1)),
              "[ 重要 ] 必ず Safari（iPhone）または Chrome（Android）で開く",
              font=warn_font, fill=ORANGE_DARK)
    warn_sub_font = font(7.5)
    draw.text((warn_x0 + mm(2), warn_y0 + mm(5.5)),
              "LINE 内ブラウザでは Google ログインができません",
              font=warn_sub_font, fill=TEXT_DIM)

    y = qr_y1 + mm(5)

    # === フッター ===
    # 区切り線
    draw.line([(PAD_X, y), (PAD_X + INNER_W, y)], fill=BORDER, width=1)
    y += mm(2)
    ft1 = "監修・開発：中村 祐介（一般社団法人チアタンブリング協会 理事 / 指導歴18年 / 元体操選手）"
    ft2 = "お問い合わせ：cheernicpro@gmail.com 　　アプリ公開URL：roadmap.cheer-tumbling.jp/"
    ft_font = font(7.5)
    fw1, _ = measure_text(draw, ft1, ft_font)
    fw2, _ = measure_text(draw, ft2, ft_font)
    draw.text((PAD_X + (INNER_W - fw1)//2, y), ft1, font=ft_font, fill=TEXT_DIM)
    y += mm(3.5)
    draw.text((PAD_X + (INNER_W - fw2)//2, y), ft2, font=ft_font, fill=TEXT_DIM)

    return img


# ===========================================================
# A3 ポスター
# ===========================================================
def make_poster_a3():
    W_MM, H_MM = 297, 420
    img = make_canvas(W_MM, H_MM)
    draw = ImageDraw.Draw(img)

    PAD_X = mm(15)
    INNER_W = mm(W_MM) - PAD_X * 2
    y = mm(12)

    # === バッジ（中央、大型） ===
    badge_text = "一般社団法人 チアタンブリング協会 公式"
    badge_font = font(16, bold=True)
    bw, bh = measure_text(draw, badge_text, badge_font)
    bx0 = (mm(W_MM) - (bw + mm(18))) // 2
    bx1 = bx0 + bw + mm(18)
    by0 = y
    by1 = by0 + bh + mm(5)
    badge_img = Image.new("RGB", (bx1-bx0, by1-by0))
    gradient_rect(badge_img, (0, 0, bx1-bx0, by1-by0), PINK, PURPLE, "diag")
    mask = Image.new("L", (bx1-bx0, by1-by0), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0,0,bx1-bx0,by1-by0), radius=mm(4.5), fill=255)
    img.paste(badge_img, (bx0, by0), mask)
    draw.text((bx0 + mm(9), by0 + mm(2.5)), badge_text, font=badge_font, fill=WHITE)
    y = by1 + mm(7)

    # === タイトル（中央、超大型） ===
    title_lines = ["チア タンブリング", "ロードマップ"]
    title_font = font(72, bold=True)
    for line in title_lines:
        tw, th = measure_text(draw, line, title_font)
        draw.text(((mm(W_MM) - tw) // 2, y), line, font=title_font, fill=PURPLE)
        y += th + mm(1)
    y += mm(5)

    # === タグライン（大型） ===
    tagline = "正しいタンブリングを、安全に、段階的に。"
    tg_font = font(26, bold=True)
    tw, th = measure_text(draw, tagline, tg_font)
    draw.text(((mm(W_MM) - tw) // 2, y), tagline, font=tg_font, fill=TEXT_DARK)
    y += th + mm(3)

    sub = "指導歴 18 年の元体操選手が監修した、指導者・選手のための練習アプリ"
    sub_font = font(16)
    sw, sh = measure_text(draw, sub, sub_font)
    draw.text(((mm(W_MM) - sw) // 2, y), sub, font=sub_font, fill=TEXT_MUTED)
    y += sh + mm(8)

    # === 数字 4 つ（白カード背景、大型） ===
    stats = [("33", "技"), ("44", "トレーニング"), ("60+", "動画解説"), ("30", "日間 無料")]
    stat_card_h = mm(34)
    stat_card_x0 = PAD_X
    stat_card_x1 = PAD_X + INNER_W
    rounded_rect(draw, (stat_card_x0, y, stat_card_x1, y + stat_card_h),
                 radius=mm(4), fill=WHITE, outline=BORDER, width=2)
    num_font = font(52, bold=True)
    lbl_font = font(14, bold=True)
    stat_w = INNER_W // 4
    for i, (num, lbl) in enumerate(stats):
        cx0 = stat_card_x0 + i * stat_w
        cx1 = cx0 + stat_w
        # 数字
        nw, nh = measure_text(draw, num, num_font)
        draw.text((cx0 + (stat_w - nw)//2, y + mm(2)), num, font=num_font, fill=PURPLE)
        # ラベル
        lw, lh = measure_text(draw, lbl, lbl_font)
        draw.text((cx0 + (stat_w - lw)//2, y + stat_card_h - mm(7.5)), lbl, font=lbl_font, fill=TEXT_MUTED)
        # 区切り縦線
        if i < len(stats) - 1:
            draw.line([(cx1, y + mm(5)), (cx1, y + stat_card_h - mm(5))],
                      fill=BORDER, width=2)
    y += stat_card_h + mm(7)

    # === iPad mockup（左）+ 機能リスト（右） ===
    row_h = mm(138)
    mock_w = mm(125)
    mock_x0 = PAD_X
    mock_y0 = y
    mock_x1 = mock_x0 + mock_w
    mock_y1 = mock_y0 + row_h
    draw_phone_mock(img, str(ROOT / "マーケティング" / "screenshots" / "app-main.png"),
                    (mock_x0, mock_y0, mock_x1, mock_y1))

    # キャプション
    cap = "↑ 実際のアプリ画面"
    cap_font = font(14, bold=True)
    cw, ch = measure_text(draw, cap, cap_font)
    draw.text((mock_x0 + (mock_w - cw)//2, mock_y1 + mm(3)),
              cap, font=cap_font, fill=TEXT_MUTED)

    # 機能リスト（右、縦並び、大型）
    feat_x0 = mock_x1 + mm(8)
    feat_x1 = PAD_X + INNER_W
    feat_w = feat_x1 - feat_x0
    features = [
        ("技ロードマップ閲覧", "レベル順・系譜図で表示、動画＋ポイント＋ミス＋進め方を網羅"),
        ("練習メニュー作成", "技とトレを組合せて保存、回数・秒数指定、共有機能あり"),
        ("選手ごとの進捗記録", "「習得中／合格」を技ごとに記録、指導者・選手が一目で把握"),
        ("練習プログラム自動生成", "人数・時間・目標技から、WU→補強→技練習までを自動提案"),
    ]
    feat_card_h = mm(30)
    feat_gap = mm(4)
    total_feat_h = feat_card_h * len(features) + feat_gap * (len(features) - 1)
    # 縦中央寄せ
    feat_start_y = mock_y0 + (row_h - total_feat_h) // 2
    ftitle_font = font(19, bold=True)
    fdesc_font = font(13)
    for idx, (title, desc) in enumerate(features):
        cy0 = feat_start_y + idx * (feat_card_h + feat_gap)
        cy1 = cy0 + feat_card_h
        rounded_rect(draw, (feat_x0, cy0, feat_x1, cy1), radius=mm(3),
                     fill=WHITE, outline=BORDER, width=1)
        # 左border（太め）
        draw.rectangle((feat_x0, cy0, feat_x0 + mm(2), cy1), fill=PURPLE)
        # 番号バッジ
        num_circle_size = mm(8)
        ncx0 = feat_x0 + mm(7)
        ncy0 = cy0 + (feat_card_h - num_circle_size) // 2
        draw.ellipse((ncx0, ncy0, ncx0 + num_circle_size, ncy0 + num_circle_size),
                     fill=PURPLE)
        num_font_small = font(13, bold=True)
        num_label = str(idx + 1)
        nlw, nlh = measure_text(draw, num_label, num_font_small)
        draw.text((ncx0 + (num_circle_size - nlw)//2 - mm(0.3),
                   ncy0 + (num_circle_size - nlh)//2 - mm(0.8)),
                  num_label, font=num_font_small, fill=WHITE)
        # タイトル
        text_x = ncx0 + num_circle_size + mm(4)
        draw.text((text_x, cy0 + mm(5)), title, font=ftitle_font, fill=TEXT_DARK)
        # 説明：折り返し
        max_w_desc = feat_x1 - text_x - mm(5)
        current_line = ""
        line_y2 = cy0 + mm(18.5)
        for ch in desc:
            test = current_line + ch
            tw, _ = measure_text(draw, test, fdesc_font)
            if tw > max_w_desc and current_line:
                draw.text((text_x, line_y2), current_line, font=fdesc_font, fill=TEXT_DIM)
                _, tlh = measure_text(draw, current_line, fdesc_font)
                line_y2 += tlh + mm(0.6)
                current_line = ch
            else:
                current_line = test
        if current_line:
            draw.text((text_x, line_y2), current_line, font=fdesc_font, fill=TEXT_DIM)

    y = mock_y1 + mm(9)

    # === QR セクション（下、横長、中央） ===
    qr_h = mm(88)
    qr_x0 = PAD_X
    qr_x1 = PAD_X + INNER_W
    qr_y0 = y
    qr_y1 = qr_y0 + qr_h
    grad_box = Image.new("RGB", (INNER_W, qr_h))
    tri_gradient_rect(grad_box, (0, 0, INNER_W, qr_h), PINK, PURPLE, CYAN, "horizontal")
    qr_mask = Image.new("L", (INNER_W, qr_h), 0)
    ImageDraw.Draw(qr_mask).rounded_rectangle((0, 0, INNER_W, qr_h), radius=mm(5), fill=255)
    img.paste(grad_box, (qr_x0, qr_y0), qr_mask)

    # 見出し（大型）
    heading = "スマホで QR を読み取って、今すぐ無料で始める"
    hd_font = font(26, bold=True)
    hw, hh = measure_text(draw, heading, hd_font)
    draw.text((qr_x0 + (INNER_W - hw)//2, qr_y0 + mm(5)), heading, font=hd_font, fill=WHITE)
    sub_qr = "クレジットカード不要・1分で開始・30日間すべての機能が無料"
    sub_qr_font = font(13)
    sw, _ = measure_text(draw, sub_qr, sub_qr_font)
    draw.text((qr_x0 + (INNER_W - sw)//2, qr_y0 + mm(16)), sub_qr, font=sub_qr_font, fill=WHITE)

    # 内側カード
    inner_x0 = qr_x0 + mm(6)
    inner_x1 = qr_x1 - mm(6)
    inner_y0 = qr_y0 + mm(26)
    inner_y1 = qr_y1 - mm(5)
    rounded_rect(draw, (inner_x0, inner_y0, inner_x1, inner_y1), radius=mm(3.5), fill=WHITE)

    # QR画像（大きく、縦中央）
    qr_size = mm(48)
    qr_path = ROOT / "マーケティング" / "qr_share.png"
    if qr_path.exists():
        qr_img = Image.open(qr_path).convert("RGB")
        qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
        qr_y_pos = inner_y0 + (inner_y1 - inner_y0 - qr_size) // 2
        img.paste(qr_img, (inner_x0 + mm(5), qr_y_pos))

    info_x = inner_x0 + qr_size + mm(13)
    info_y = inner_y0 + mm(5)
    scan_font = font(16, bold=True)
    draw.text((info_x, info_y), "QR スキャン または下記URLへ", font=scan_font, fill=TEXT_DARK)
    info_y += mm(8)
    url_font = font(14, bold=True)
    draw.text((info_x, info_y), "roadmap.cheer-tumbling.jp/", font=url_font, fill=PURPLE_DARK)
    info_y += mm(9)
    # 警告
    warn_x0 = info_x
    warn_x1 = inner_x1 - mm(6)
    warn_y0 = info_y
    warn_y1 = warn_y0 + mm(20)
    rounded_rect(draw, (warn_x0, warn_y0, warn_x1, warn_y1), radius=mm(2),
                 fill=ORANGE_LIGHT, outline=ORANGE, width=2)
    wfont = font(13, bold=True)
    draw.text((warn_x0 + mm(3.5), warn_y0 + mm(2.5)),
              "[ 重要 ] 必ず Safari（iPhone）または Chrome（Android）で開く",
              font=wfont, fill=ORANGE_DARK)
    wsfont = font(11)
    draw.text((warn_x0 + mm(3.5), warn_y0 + mm(11)),
              "LINE 内ブラウザでは Google ログインに対応していません",
              font=wsfont, fill=TEXT_MUTED)

    y = qr_y1 + mm(5)

    # フッター（大型）
    draw.line([(PAD_X, y), (PAD_X + INNER_W, y)], fill=BORDER, width=2)
    y += mm(2.5)
    ft1 = "監修・開発：中村 祐介（一般社団法人チアタンブリング協会 理事 / 指導歴18年 / 元体操選手 / SCB BULLETS 代表）"
    ft2 = "お問い合わせ：cheernicpro@gmail.com 　　アプリ公開URL：roadmap.cheer-tumbling.jp/"
    ftf = font(10.5)
    for ft in [ft1, ft2]:
        ftw, fth = measure_text(draw, ft, ftf)
        draw.text(((mm(W_MM) - ftw) // 2, y), ft, font=ftf, fill=TEXT_DIM)
        y += fth + mm(1.5)

    return img


# ===========================================================
# 実行
# ===========================================================
def main():
    print("📄 A4 チラシ生成中...")
    flyer = make_flyer_a4()
    flyer_pdf = OUT_DIR / "flyer_a4_print.pdf"
    flyer.save(flyer_pdf, "PDF", resolution=DPI)
    print(f"  ✅ {flyer_pdf} ({flyer.size[0]}x{flyer.size[1]}px)")

    print("📰 A3 ポスター生成中...")
    poster = make_poster_a3()
    poster_pdf = OUT_DIR / "poster_a3_print.pdf"
    poster.save(poster_pdf, "PDF", resolution=DPI)
    print(f"  ✅ {poster_pdf} ({poster.size[0]}x{poster.size[1]}px)")

    # デスクトップにもコピー
    today = datetime.now().strftime("%Y%m%d")
    desktop_dir = Path.home() / "Desktop" / f"タンブリングロードマップ_配布物_{today}"
    desktop_dir.mkdir(exist_ok=True)
    import shutil
    for src in [flyer_pdf, poster_pdf]:
        shutil.copy(src, desktop_dir / src.name)
    print(f"\n📁 デスクトップにコピー: {desktop_dir}")

    print("\n完了 ✨")


if __name__ == "__main__":
    main()
