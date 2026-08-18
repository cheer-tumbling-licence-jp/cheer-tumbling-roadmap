#!/usr/bin/env python3
"""
Instagram フィード（4:5 = 1080x1350）の販促物カルーセル 6 枚
告知用：あなたの練習に、答えを。/ 完全無料 / コーチ / 選手 / 保護者 / プラン

出力：マーケティング/sns_release/promo_feed_NN_NAME.png
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).parent))
from make_print_flyer import (
    PURPLE, PURPLE_DARK, PINK, CYAN, GOLD,
    DARK_BG, DARK_BG_2, WHITE, TEXT_DIM, TEXT_MUTED,
    ORANGE, ORANGE_DARK,
    gradient_rect, rounded_rect, text_centered, measure_text,
)

ROOT = Path(__file__).parent.parent
OUT_DIR = ROOT / "マーケティング" / "sns_release"
OUT_DIR.mkdir(exist_ok=True)
SHOTS = ROOT / "assets" / "lp-screenshots"

# === Canvas: 1080 x 1350 (Instagram フィード 4:5) ===
W = 1080
H = 1350

# Fonts (日本語)
FONT_JP_REG = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
FONT_JP_BLD = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
FONT_JP_BLK = "/System/Library/Fonts/ヒラギノ角ゴシック W8.ttc"


def font(size_px, weight="reg"):
    path = {
        "reg": FONT_JP_REG,
        "bold": FONT_JP_BLD,
        "black": FONT_JP_BLK,
    }[weight]
    return ImageFont.truetype(path, size_px)


GOLD_BRIGHT = (255, 220, 60)
YELLOW_PALE = (255, 248, 200)
DARK_TEXT = (45, 30, 70)


def paste_screenshot_full(canvas, path, xy_box, radius=24):
    """xy_box にスクショを縦横比保持でフィット（余白あり）"""
    x0, y0, x1, y1 = xy_box
    w, h = x1 - x0, y1 - y0
    if not Path(path).exists():
        d = ImageDraw.Draw(canvas)
        rounded_rect(d, xy_box, radius, fill=(50, 35, 80), outline=(80, 60, 110), width=3)
        text_centered(d, xy_box, "[ App Screen ]", font(40, "bold"), (140, 130, 170))
        return
    img = Image.open(path).convert("RGB")
    # 縦横比保持で内側にフィット
    scale = min(w / img.width, h / img.height)
    nw, nh = int(img.width * scale), int(img.height * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    mask = Image.new("L", (nw, nh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, nw, nh), radius=radius, fill=255)
    canvas.paste(img, (x0 + (w - nw) // 2, y0 + (h - nh) // 2), mask)


def draw_phone_frame_with_shot(canvas, screenshot_path, xy_box):
    """iPhone風フレーム（角丸黒枠+ノッチ+ホームバー）にスクショを埋め込む"""
    x0, y0, x1, y1 = xy_box
    w, h = x1 - x0, y1 - y0
    d = ImageDraw.Draw(canvas)
    # 影
    shadow = Image.new("RGBA", (w + 60, h + 60), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((30, 30, w + 30, h + 30), radius=48, fill=(0, 0, 0, 120))
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    canvas.paste(shadow, (x0 - 30, y0 - 30), shadow)
    # フレーム（黒）
    rounded_rect(d, (x0, y0, x1, y1), 48, fill=(15, 10, 25), outline=(60, 50, 80), width=2)
    # スクリーンエリア（内側）
    pad = 16
    sx0, sy0, sx1, sy1 = x0 + pad, y0 + pad + 18, x1 - pad, y1 - pad - 18
    paste_screenshot_full(canvas, screenshot_path, (sx0, sy0, sx1, sy1), radius=32)
    # ノッチ
    notch_w, notch_h = 180, 26
    nx = x0 + (w - notch_w) // 2
    ny = y0 + 12
    d.rounded_rectangle((nx, ny, nx + notch_w, ny + notch_h), radius=14, fill=(15, 10, 25))
    # ホームバー
    bar_w, bar_h = 220, 5
    bx = x0 + (w - bar_w) // 2
    by = y1 - 14
    d.rounded_rectangle((bx, by, bx + bar_w, by + bar_h), radius=3, fill=(200, 195, 220))


def gen_qr_hi(url, out_path):
    """印刷・読み取り強化型 QR (誤り訂正 H・ドット大)"""
    try:
        import qrcode
        from qrcode.constants import ERROR_CORRECT_H
        qr = qrcode.QRCode(version=None, error_correction=ERROR_CORRECT_H, box_size=24, border=2)
        qr.add_data(url); qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        img.save(out_path)
        return True
    except Exception as e:
        print("QR gen failed:", e)
        return False


def draw_common_top_strip(canvas, idx_str=None, badge_text="今日リリース"):
    """共通：左上に協会名、右上に "今日リリース" バッジ、最上部に細いグラデ帯"""
    d = ImageDraw.Draw(canvas)
    # 細いグラデ帯（最上部）
    band_h = 6
    bi = Image.new("RGB", (W, band_h))
    gradient_rect(bi, (0, 0, W, band_h), PINK, CYAN, "horizontal")
    canvas.paste(bi, (0, 0))
    # 協会名（左上）
    d.text((44, 26), "● 一般社団法人 チアタンブリング協会  公式アプリ",
           font=font(22, "reg"), fill=(220, 215, 240))
    # バッジ（右上）
    bw, bh = 220, 64
    bx = W - 44 - bw
    by = 22
    bg = Image.new("RGB", (bw, bh))
    gradient_rect(bg, (0, 0, bw, bh), (255, 75, 110), ORANGE, "diag")
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), radius=32, fill=255)
    canvas.paste(bg, (bx, by), mask)
    text_centered(d, (bx, by, bx + bw, by + bh), badge_text, font(30, "black"), WHITE)
    # ページインジケーター
    if idx_str:
        d.text((W - 64, H - 50), idx_str, font=font(22, "bold"), fill=(160, 150, 195))


def draw_common_bottom_strip(canvas, cta_text="@cheer_tumbling / roadmap.cheer-tumbling.jp"):
    """共通：下部に細いCTA帯"""
    d = ImageDraw.Draw(canvas)
    # 下端のグラデ帯
    band_h = 64
    bi = Image.new("RGB", (W, band_h))
    gradient_rect(bi, (0, 0, W, band_h), PURPLE_DARK, PINK, "horizontal")
    canvas.paste(bi, (0, H - band_h))
    text_centered(d, (0, H - band_h, W, H), cta_text, font(26, "bold"), WHITE)


# ===========================================================
# 1/6 ヒーロー：「あなたの練習に、答えを。」+ QR大 + アプリ画面
# 目的：今日リリース → 即読み取って使ってもらう
# ===========================================================
def slide_1_hero():
    # 背景：暗紫グラデ
    canvas = Image.new("RGB", (W, H), DARK_BG)
    bg = Image.new("RGB", (W, H))
    gradient_rect(bg, (0, 0, W, H), DARK_BG_2, DARK_BG, "vertical")
    canvas.paste(bg, (0, 0))

    # 装飾光
    for cx, cy, color in [(120, 200, (236, 72, 153)), (W - 200, H - 300, (6, 182, 212))]:
        glow = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for r, alpha in [(350, 30), (250, 50), (150, 80)]:
            gd.ellipse((350 - r, 350 - r, 350 + r, 350 + r), fill=(*color, alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(60))
        canvas.paste(glow, (cx - 350, cy - 350), glow)

    d = ImageDraw.Draw(canvas)
    draw_common_top_strip(canvas, idx_str="1/6", badge_text="リリース！")

    # キャッチ（コンパクトに上部）
    title_y = 130
    d.text((64, title_y), "あなたの練習に、", font=font(78, "black"), fill=WHITE)
    title_y += 90
    main_text = "答えを。"
    main_font = font(110, "black")
    d.text((64, title_y), main_text, font=main_font, fill=GOLD_BRIGHT)
    title_y += 130

    # サブ
    d.text((64, title_y), "33技 + 44トレ + 解説動画105本", font=font(34, "bold"), fill=(220, 215, 240))
    d.text((64, title_y + 50), "チア指導のプロが作った、上達アプリ", font=font(28, "reg"), fill=(180, 175, 210))

    # === メインビジュアル：左にスマホ、右に大QR ===
    mid_y = 620
    phone_w, phone_h = 300, 600
    px = 70
    draw_phone_frame_with_shot(
        canvas, str(SHOTS / "mobile" / "01_home.png"),
        (px, mid_y, px + phone_w, mid_y + phone_h),
    )

    # === QR カード（右）— ヘッダ込みで一体化 ===
    qr_box_size = 380
    card_pad = 24
    qx = W - qr_box_size - card_pad - 60
    qy = mid_y + 80  # ヘッダの分下げる
    card_x0 = qx - card_pad
    card_y0 = mid_y
    card_x1 = qx + qr_box_size + card_pad
    card_y1 = qy + qr_box_size + 95

    # 白カード（影付き）
    shadow = Image.new("RGBA", (card_x1 - card_x0 + 60, card_y1 - card_y0 + 60), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle((30, 30, (card_x1 - card_x0) + 30, (card_y1 - card_y0) + 30),
                         radius=28, fill=(0, 0, 0, 100))
    shadow = shadow.filter(ImageFilter.GaussianBlur(15))
    canvas.paste(shadow, (card_x0 - 30, card_y0 - 30), shadow)
    d.rounded_rectangle((card_x0, card_y0, card_x1, card_y1),
                        radius=28, fill=WHITE, outline=GOLD_BRIGHT, width=6)
    # カード上部：黄色帯「いますぐ読み取って使う」
    header_h = 70
    hi = Image.new("RGB", (card_x1 - card_x0, header_h))
    gradient_rect(hi, (0, 0, card_x1 - card_x0, header_h), GOLD_BRIGHT, (255, 200, 30), "horizontal")
    hm = Image.new("L", (card_x1 - card_x0, header_h), 0)
    ImageDraw.Draw(hm).rounded_rectangle((0, 0, card_x1 - card_x0, header_h),
                                          radius=24, fill=255)
    # 下側角を直角に
    ImageDraw.Draw(hm).rectangle((0, header_h // 2, card_x1 - card_x0, header_h), fill=255)
    canvas.paste(hi, (card_x0, card_y0), hm)
    text_centered(d, (card_x0, card_y0, card_x1, card_y0 + header_h),
                  "いますぐ読み取って使う", font(30, "black"), DARK_TEXT)
    # QR
    qr_path = OUT_DIR / "_promo_feed_qr.png"
    gen_qr_hi("https://roadmap.cheer-tumbling.jp/", str(qr_path))
    if qr_path.exists():
        qr_img = Image.open(qr_path).convert("RGB").resize((qr_box_size, qr_box_size), Image.LANCZOS)
        canvas.paste(qr_img, (qx, qy + 0))
    # URL（カード内・QR下）
    url_y = qy + qr_box_size + 12
    text_centered(d, (card_x0, url_y, card_x1, url_y + 30),
                  "roadmap.cheer-tumbling.jp", font(22, "bold"), DARK_TEXT)
    text_centered(d, (card_x0, url_y + 32, card_x1, url_y + 56),
                  "スマホのカメラで読み取り", font(16, "reg"), (110, 90, 140))

    # === 完全無料 訴求（スマホ下、画面外にはみ出さない） ===
    free_y = mid_y + phone_h + 28
    # 黄色チップ「完全無料」
    fchip_w, fchip_h = phone_w, 50
    fchip = Image.new("RGB", (fchip_w, fchip_h))
    gradient_rect(fchip, (0, 0, fchip_w, fchip_h), GOLD_BRIGHT, (255, 200, 30), "horizontal")
    fmask = Image.new("L", (fchip_w, fchip_h), 0)
    ImageDraw.Draw(fmask).rounded_rectangle((0, 0, fchip_w, fchip_h), radius=14, fill=255)
    canvas.paste(fchip, (px, free_y), fmask)
    text_centered(d, (px, free_y, px + fchip_w, free_y + fchip_h),
                  "基本機能 完全無料", font(24, "black"), DARK_TEXT)
    # 補足
    d.text((px, free_y + fchip_h + 8),
           "動画 / メニュー作成 / 記録、すぐ使えます", font=font(16, "reg"), fill=(200, 195, 220))

    draw_common_bottom_strip(canvas, "roadmap.cheer-tumbling.jp ／ チアタンブリングロードマップ")

    out = OUT_DIR / "promo_feed_01_hero.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"✓ {out}")


# ===========================================================
# 共通：紫グラデ背景キャンバス
# ===========================================================
def make_bg(w=W, h=H, color_a=DARK_BG_2, color_b=DARK_BG, glow_a=(236, 72, 153), glow_b=(6, 182, 212)):
    canvas = Image.new("RGB", (w, h), DARK_BG)
    bg = Image.new("RGB", (w, h))
    gradient_rect(bg, (0, 0, w, h), color_a, color_b, "vertical")
    canvas.paste(bg, (0, 0))
    for cx, cy, color in [(120, 200, glow_a), (w - 200, h - 300, glow_b)]:
        glow = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for r, alpha in [(350, 30), (250, 50), (150, 80)]:
            gd.ellipse((350 - r, 350 - r, 350 + r, 350 + r), fill=(*color, alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(60))
        canvas.paste(glow, (cx - 350, cy - 350), glow)
    return canvas


def draw_slide_header(canvas, idx_str, badge=None, badge_color=(255, 75, 110)):
    d = ImageDraw.Draw(canvas)
    band_h = 6
    bi = Image.new("RGB", (W, band_h))
    gradient_rect(bi, (0, 0, W, band_h), PINK, CYAN, "horizontal")
    canvas.paste(bi, (0, 0))
    d.text((44, 26), "● 一般社団法人 チアタンブリング協会  公式アプリ",
           font=font(22, "reg"), fill=(220, 215, 240))
    if badge:
        bw, bh = 220, 56
        bx, by = W - 44 - bw, 22
        bg = Image.new("RGB", (bw, bh))
        gradient_rect(bg, (0, 0, bw, bh), badge_color, ORANGE, "diag")
        mask = Image.new("L", (bw, bh), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), radius=28, fill=255)
        canvas.paste(bg, (bx, by), mask)
        text_centered(d, (bx, by, bx + bw, by + bh), badge, font(26, "black"), WHITE)
    d.text((W - 80, H - 50), idx_str, font=font(22, "bold"), fill=(160, 150, 195))


def draw_slide_footer(canvas, cta="roadmap.cheer-tumbling.jp ／ いますぐQR読み取り"):
    d = ImageDraw.Draw(canvas)
    band_h = 64
    bi = Image.new("RGB", (W, band_h))
    gradient_rect(bi, (0, 0, W, band_h), PURPLE_DARK, PINK, "horizontal")
    canvas.paste(bi, (0, H - band_h))
    text_centered(d, (0, H - band_h, W, H), cta, font(26, "bold"), WHITE)


def draw_swipe_hint(canvas):
    """次へスワイプの誘導を右下に小さく"""
    d = ImageDraw.Draw(canvas)
    d.text((W - 200, H - 110), "次へスワイプ ▶", font=font(20, "bold"), fill=(200, 195, 220))


# ===========================================================
# 2/6 「すべての技に、解説動画」
# ===========================================================
def slide_2_videos():
    canvas = make_bg()
    draw_slide_header(canvas, "2/6", "解説動画 105本", (138, 43, 226))
    d = ImageDraw.Draw(canvas)
    # キャッチ
    d.text((64, 140), "すべての技に、", font=font(70, "black"), fill=WHITE)
    d.text((64, 220), "解説動画。", font=font(108, "black"), fill=GOLD_BRIGHT)
    # サブ
    d.text((64, 360),
           "33技 + 44トレ、ぜんぶ動画つき。",
           font=font(34, "bold"), fill=(220, 215, 240))
    d.text((64, 408),
           "見て・真似て・反復、迷わない。",
           font=font(28, "reg"), fill=(180, 175, 210))

    # 左にスマホ（技詳細 = バク転動画）
    phone_w, phone_h = 380, 760
    px = 70
    py = 510
    draw_phone_frame_with_shot(canvas, str(SHOTS / "mobile" / "03_skill_detail.png"),
                               (px, py, px + phone_w, py + phone_h))

    # 右側：3つの強み
    rx = 520
    ry = 540
    bullets = [
        ("✓", "105本", "すべて公式YouTube連携"),
        ("✓", "段階別", "Lv1〜Lv6 のやさしい級分け"),
        ("✓", "安全評価", "危険度・補助の要否を明示"),
    ]
    for i, (mark, head, body) in enumerate(bullets):
        cy = ry + i * 150
        # 円バッジ
        d.ellipse((rx, cy, rx + 60, cy + 60), fill=GOLD_BRIGHT)
        text_centered(d, (rx, cy, rx + 60, cy + 60), mark, font(36, "black"), DARK_TEXT)
        d.text((rx + 80, cy + 2), head, font=font(46, "black"), fill=WHITE)
        d.text((rx + 80, cy + 62), body, font=font(24, "reg"), fill=(200, 195, 220))

    draw_swipe_hint(canvas)
    draw_slide_footer(canvas)
    out = OUT_DIR / "promo_feed_02_videos.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"✓ {out}")


# ===========================================================
# 3/6 コーチ機能：練習プログラム自動生成＋指導配置図
# ===========================================================
def slide_3_coach():
    canvas = make_bg(glow_a=(138, 43, 226), glow_b=(236, 72, 153))
    draw_slide_header(canvas, "3/6", "コーチ向け", PURPLE_DARK)
    d = ImageDraw.Draw(canvas)
    d.text((64, 140), "コーチの仕事を、", font=font(64, "black"), fill=WHITE)
    d.text((64, 220), "半分に。", font=font(110, "black"), fill=GOLD_BRIGHT)
    d.text((64, 370),
           "人数・指導者数・目標技を入れるだけ。", font=font(30, "bold"), fill=(220, 215, 240))
    d.text((64, 412),
           "AIが「安全に回せる」サーキット練習を自動設計。", font=font(24, "reg"), fill=(180, 175, 210))

    # スクショ（横長）desktop/01_program_circuit
    sx, sy, sw, sh = 60, 490, W - 120, 540
    rounded_rect(d, (sx - 8, sy - 8, sx + sw + 8, sy + sh + 8),
                 24, fill=(255, 255, 255), outline=GOLD_BRIGHT, width=4)
    paste_screenshot_full(canvas, str(SHOTS / "desktop" / "01_program_circuit.png"),
                          (sx, sy, sx + sw, sy + sh), radius=18)
    # 説明バブル
    d.text((64, 1060),
           "● 指導者の配置を図で表示 / ステーション5段階 / 1グループ◯人",
           font=font(22, "bold"), fill=GOLD_BRIGHT)
    d.text((64, 1100),
           "目標：選手15名 / 指導者1名 でも安全に回せる練習設計を支援。",
           font=font(20, "reg"), fill=(200, 195, 220))

    draw_swipe_hint(canvas)
    draw_slide_footer(canvas)
    out = OUT_DIR / "promo_feed_03_coach.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"✓ {out}")


# ===========================================================
# 4/6 選手機能：ヒートマップ・自主トレメ作成・ストリーク
# ===========================================================
def slide_4_athlete():
    canvas = make_bg(glow_a=(6, 182, 212), glow_b=(255, 220, 60))
    draw_slide_header(canvas, "4/6", "選手向け", CYAN)
    d = ImageDraw.Draw(canvas)
    d.text((64, 140), "練習が見える、", font=font(70, "black"), fill=WHITE)
    d.text((64, 222), "伸びが続く。", font=font(110, "black"), fill=GOLD_BRIGHT)
    d.text((64, 370),
           "自分のメニュー作成、毎日の記録、達成率を可視化。", font=font(28, "bold"), fill=(220, 215, 240))
    d.text((64, 412),
           "「練習が続く理由」が、ここにある。", font=font(26, "reg"), fill=(180, 175, 210))

    # スクショ（横長）desktop/02_progress_heatmap
    sx, sy, sw, sh = 60, 490, W - 120, 540
    rounded_rect(d, (sx - 8, sy - 8, sx + sw + 8, sy + sh + 8),
                 24, fill=WHITE, outline=GOLD_BRIGHT, width=4)
    paste_screenshot_full(canvas, str(SHOTS / "desktop" / "02_progress_heatmap.png"),
                          (sx, sy, sx + sw, sy + sh), radius=18)

    # 強み3つ
    d.text((64, 1060),
           "● 達成率の可視化 ／ レベル別バー ／ 30日連続でプレミアム動画解放",
           font=font(22, "bold"), fill=GOLD_BRIGHT)
    d.text((64, 1100),
           "頑張った日が色で塗られる。続けたい気持ちが、ずっと続く。",
           font=font(20, "reg"), fill=(200, 195, 220))
    draw_swipe_hint(canvas)
    draw_slide_footer(canvas)
    out = OUT_DIR / "promo_feed_04_athlete.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"✓ {out}")


# ===========================================================
# 5/6 保護者向け：安全・段階性・国際ライセンス
# ===========================================================
def slide_5_parent():
    canvas = make_bg(glow_a=(236, 72, 153), glow_b=(255, 220, 60))
    draw_slide_header(canvas, "5/6", "保護者の方へ", PINK)
    d = ImageDraw.Draw(canvas)
    d.text((64, 140), "保護者の", font=font(70, "black"), fill=WHITE)
    d.text((64, 220), "あなたへ。", font=font(110, "black"), fill=GOLD_BRIGHT)
    d.text((64, 370),
           "安全と、段階性で、お子様の挑戦をサポート。", font=font(30, "bold"), fill=(220, 215, 240))
    d.text((64, 412),
           "国際ライセンス保有者監修。危険な近道はさせません。", font=font(24, "reg"), fill=(180, 175, 210))

    # スマホ（技詳細 = USA Lv 表示）
    phone_w, phone_h = 380, 760
    px = 70
    py = 500
    draw_phone_frame_with_shot(canvas, str(SHOTS / "mobile" / "03_skill_detail.png"),
                               (px, py, px + phone_w, py + phone_h))

    # 右側 強みリスト
    rx = 520
    ry = 530
    bullets = [
        ("●", "段階性", "Lv1〜Lv6 の段階別ロードマップ"),
        ("●", "安全評価", "技ごとに危険度を明示"),
        ("●", "成長記録", "達成率・努力の日数で見える"),
        ("●", "監修者", "中村 祐介 / 前島 一貴"),
    ]
    for i, (mark, head, body) in enumerate(bullets):
        cy = ry + i * 130
        d.ellipse((rx, cy, rx + 54, cy + 54), fill=GOLD_BRIGHT)
        text_centered(d, (rx, cy, rx + 54, cy + 54), mark, font(30, "black"), DARK_TEXT)
        d.text((rx + 70, cy + 0), head, font=font(38, "black"), fill=WHITE)
        d.text((rx + 70, cy + 55), body, font=font(20, "reg"), fill=(200, 195, 220))

    draw_swipe_hint(canvas)
    draw_slide_footer(canvas)
    out = OUT_DIR / "promo_feed_05_parent.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"✓ {out}")


# ===========================================================
# 6/6 プラン + QR大（クロージング）
# ===========================================================
def slide_6_plan_qr():
    canvas = make_bg(glow_a=(255, 220, 60), glow_b=(236, 72, 153))
    draw_slide_header(canvas, "6/6", "本日リリース", (255, 75, 110))
    d = ImageDraw.Draw(canvas)
    # クロージングメッセージ
    d.text((64, 140), "あとは、", font=font(70, "black"), fill=WHITE)
    d.text((64, 220), "読み取るだけ。", font=font(96, "black"), fill=GOLD_BRIGHT)

    # === プラン縦リスト（左） ===
    plans_y = 380
    plans_x = 64
    plans = [
        ("フリー", "¥0/月", "動画・トレメ・記録 まるごと無料", GOLD_BRIGHT, True),
        ("個人", "¥480/月", "プレミアム動画も解放", PURPLE, False),
        ("コーチ", "¥1,200/月", "教室 〜10名", PURPLE, False),
        ("コーチプラス", "¥1,980/月", "大規模チーム 無制限", PURPLE, False),
        ("トレーニング指導 NEW", "¥4,500/月", "個別メニュー＋動画添削月20本", ORANGE, False),
        ("完全1on1 NEW", "¥7,500/月", "添削無制限＋専用LINE＋月1通話", PINK, False),
    ]
    for i, (name, price, desc, color, hi) in enumerate(plans):
        py = plans_y + i * 92
        row_w = 540
        if hi:
            rounded_rect(d, (plans_x, py, plans_x + row_w, py + 80),
                         12, fill=(255, 248, 200), outline=GOLD_BRIGHT, width=3)
            d.text((plans_x + 14, py + 4), name, font=font(20, "bold"), fill=(140, 100, 0))
            d.text((plans_x + 14, py + 30), price, font=font(34, "black"), fill=(180, 130, 0))
            d.text((plans_x + 280, py + 36), desc, font=font(18, "reg"), fill=(120, 90, 0))
        else:
            rounded_rect(d, (plans_x, py, plans_x + row_w, py + 80),
                         12, fill=(50, 35, 80), outline=(80, 60, 110), width=2)
            d.text((plans_x + 14, py + 4), name, font=font(20, "bold"), fill=WHITE)
            d.text((plans_x + 14, py + 30), price, font=font(34, "black"), fill=color)
            d.text((plans_x + 280, py + 36), desc, font=font(18, "reg"), fill=(200, 195, 220))

    # === QR + URL（右下） ===
    qr_box = 380
    qx = W - qr_box - 80
    qy = 600
    # 白カード
    cp = 20
    d.rounded_rectangle((qx - cp, qy - cp - 60, qx + qr_box + cp, qy + qr_box + cp + 70),
                        radius=20, fill=WHITE, outline=GOLD_BRIGHT, width=5)
    # ヘッダ「いま読み取る」
    hi = Image.new("RGB", (qr_box + cp * 2, 60))
    gradient_rect(hi, (0, 0, qr_box + cp * 2, 60), GOLD_BRIGHT, (255, 200, 30), "horizontal")
    hm = Image.new("L", (qr_box + cp * 2, 60), 0)
    ImageDraw.Draw(hm).rounded_rectangle((0, 0, qr_box + cp * 2, 60), radius=18, fill=255)
    ImageDraw.Draw(hm).rectangle((0, 30, qr_box + cp * 2, 60), fill=255)
    canvas.paste(hi, (qx - cp, qy - cp - 60), hm)
    text_centered(d, (qx - cp, qy - cp - 60, qx + qr_box + cp, qy - cp),
                  "30日無料体験中", font(26, "black"), DARK_TEXT)
    # QR
    qr_path = OUT_DIR / "_promo_feed_qr.png"
    gen_qr_hi("https://roadmap.cheer-tumbling.jp/", str(qr_path))
    if qr_path.exists():
        qr_img = Image.open(qr_path).convert("RGB").resize((qr_box, qr_box), Image.LANCZOS)
        canvas.paste(qr_img, (qx, qy))
    # URL
    text_centered(d, (qx - cp, qy + qr_box + 8, qx + qr_box + cp, qy + qr_box + 50),
                  "roadmap.cheer-tumbling.jp", font(22, "bold"), DARK_TEXT)

    draw_slide_footer(canvas, "roadmap.cheer-tumbling.jp ／ いますぐQR読み取り")
    out = OUT_DIR / "promo_feed_06_plan_qr.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"✓ {out}")


# ===========================================================
# Story (9:16 = 1080x1920) 圧縮版
# ===========================================================
def slide_story():
    SW, SH = 1080, 1920
    canvas = Image.new("RGB", (SW, SH), DARK_BG)
    bg = Image.new("RGB", (SW, SH))
    gradient_rect(bg, (0, 0, SW, SH), DARK_BG_2, DARK_BG, "vertical")
    canvas.paste(bg, (0, 0))
    for cx, cy, color in [(120, 300, (236, 72, 153)), (SW - 200, SH - 400, (6, 182, 212))]:
        glow = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        for r, alpha in [(350, 30), (250, 50), (150, 80)]:
            gd.ellipse((350 - r, 350 - r, 350 + r, 350 + r), fill=(*color, alpha))
        glow = glow.filter(ImageFilter.GaussianBlur(60))
        canvas.paste(glow, (cx - 350, cy - 350), glow)

    d = ImageDraw.Draw(canvas)
    # トップ帯
    band = Image.new("RGB", (SW, 6))
    gradient_rect(band, (0, 0, SW, 6), PINK, CYAN, "horizontal")
    canvas.paste(band, (0, 0))
    d.text((44, 26), "● 一般社団法人 チアタンブリング協会  公式アプリ",
           font=font(24, "reg"), fill=(220, 215, 240))
    # バッジ
    bw, bh = 240, 60
    bx, by = SW - 44 - bw, 22
    bg_b = Image.new("RGB", (bw, bh))
    gradient_rect(bg_b, (0, 0, bw, bh), (255, 75, 110), ORANGE, "diag")
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), radius=30, fill=255)
    canvas.paste(bg_b, (bx, by), mask)
    text_centered(d, (bx, by, bx + bw, by + bh), "本日リリース", font(28, "black"), WHITE)

    # キャッチ
    d.text((64, 200), "あなたの練習に、", font=font(82, "black"), fill=WHITE)
    d.text((64, 300), "答えを。", font=font(140, "black"), fill=GOLD_BRIGHT)
    d.text((64, 470),
           "33技 + 44トレ + 解説動画105本",
           font=font(38, "bold"), fill=(220, 215, 240))
    d.text((64, 520),
           "チア指導のプロが作った、上達アプリ",
           font=font(30, "reg"), fill=(180, 175, 210))

    # 中央：iPhone（大）
    phone_w, phone_h = 460, 920
    px = (SW - phone_w) // 2
    py = 620
    draw_phone_frame_with_shot(canvas, str(SHOTS / "mobile" / "01_home.png"),
                               (px, py, px + phone_w, py + phone_h))

    # QR + 「読み取る」CTA（下部）
    qr_box = 360
    qx = SW - qr_box - 80
    qy = SH - 600
    cp = 24
    d.rounded_rectangle((qx - cp, qy - cp - 60, qx + qr_box + cp, qy + qr_box + cp + 60),
                        radius=24, fill=WHITE, outline=GOLD_BRIGHT, width=6)
    hi = Image.new("RGB", (qr_box + cp * 2, 60))
    gradient_rect(hi, (0, 0, qr_box + cp * 2, 60), GOLD_BRIGHT, (255, 200, 30), "horizontal")
    hm = Image.new("L", (qr_box + cp * 2, 60), 0)
    ImageDraw.Draw(hm).rounded_rectangle((0, 0, qr_box + cp * 2, 60), radius=20, fill=255)
    ImageDraw.Draw(hm).rectangle((0, 30, qr_box + cp * 2, 60), fill=255)
    canvas.paste(hi, (qx - cp, qy - cp - 60), hm)
    text_centered(d, (qx - cp, qy - cp - 60, qx + qr_box + cp, qy - cp),
                  "いますぐ読み取って使う", font(28, "black"), DARK_TEXT)
    qr_path = OUT_DIR / "_promo_feed_qr.png"
    gen_qr_hi("https://roadmap.cheer-tumbling.jp/", str(qr_path))
    if qr_path.exists():
        qr_img = Image.open(qr_path).convert("RGB").resize((qr_box, qr_box), Image.LANCZOS)
        canvas.paste(qr_img, (qx, qy))
    text_centered(d, (qx - cp, qy + qr_box + 8, qx + qr_box + cp, qy + qr_box + 50),
                  "roadmap.cheer-tumbling.jp", font(22, "bold"), DARK_TEXT)

    # 左下：完全無料訴求
    free_y = SH - 540
    fchip_w, fchip_h = 380, 80
    fchip = Image.new("RGB", (fchip_w, fchip_h))
    gradient_rect(fchip, (0, 0, fchip_w, fchip_h), GOLD_BRIGHT, (255, 200, 30), "horizontal")
    fmask = Image.new("L", (fchip_w, fchip_h), 0)
    ImageDraw.Draw(fmask).rounded_rectangle((0, 0, fchip_w, fchip_h), radius=22, fill=255)
    canvas.paste(fchip, (64, free_y), fmask)
    text_centered(d, (64, free_y, 64 + fchip_w, free_y + fchip_h),
                  "基本機能 完全無料", font(32, "black"), DARK_TEXT)
    d.text((64, free_y + fchip_h + 18),
           "動画 / メニュー作成 / 記録、すべて", font=font(24, "reg"), fill=(200, 195, 220))
    d.text((64, free_y + fchip_h + 54),
           "アカウント登録ナシで使えます", font=font(24, "reg"), fill=(200, 195, 220))

    # 下端帯
    band_h = 80
    bi = Image.new("RGB", (SW, band_h))
    gradient_rect(bi, (0, 0, SW, band_h), PURPLE_DARK, PINK, "horizontal")
    canvas.paste(bi, (0, SH - band_h))
    text_centered(d, (0, SH - band_h, SW, SH),
                  "roadmap.cheer-tumbling.jp ／ チアタンブリングロードマップ",
                  font(28, "bold"), WHITE)

    out = OUT_DIR / "promo_story_01_hero.png"
    canvas.save(out, "PNG", optimize=True)
    print(f"✓ {out}")


if __name__ == "__main__":
    slide_1_hero()
    slide_2_videos()
    slide_3_coach()
    slide_4_athlete()
    slide_5_parent()
    slide_6_plan_qr()
    slide_story()
