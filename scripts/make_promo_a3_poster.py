#!/usr/bin/env python3
"""
A3 ポスター版：LP の全体像を1枚にまとめた掲示物用大型 PDF

A3 縦 (297 x 420mm) 300DPI = 3508 x 4961 px
含まれる要素：
- ヘッダ + 業界初バッジ
- ヒーロー：大タイトル + サブ + 数字バー
- 完全無料アピール帯
- 最新アップデート 6カード
- 3者別ストリップ（コーチ/保護者/選手）
- 目玉機能 2つ（大）
- コーチ機能その他 4カード（スクショ付き）
- 3ステップで始められます
- 全プラン一覧（6プラン）
- 監修者
- 大QR + CTA + URL

出力：マーケティング/pdf/promo_a3_poster.pdf
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

W_MM, H_MM = 297, 420
PAD_X = mm(14)


def draw_header(canvas, y0):
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0 + mm(3)), "一般社団法人 チアタンブリング協会  公式アプリ",
           font=font(12, bold=False), fill=TEXT_MUTED)
    # 業界初！バッジ
    bw, bh = mm(30), mm(11)
    bx = mm(W_MM) - PAD_X - bw
    by = y0
    badge_img = Image.new("RGB", (bw, bh))
    gradient_rect(badge_img, (0, 0, bw, bh), RED_NEW, ORANGE, "horizontal")
    mask = Image.new("L", (bw, bh), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bw, bh), radius=mm(5.5), fill=255)
    canvas.paste(badge_img, (bx, by), mask)
    text_centered(d, (bx, by, bx + bw, by + bh), "業界初！", font(16, bold=True), WHITE)
    return y0 + mm(14)


def draw_hero(canvas, y0):
    d = ImageDraw.Draw(canvas)
    title_f = font(46, bold=True)
    d.text((PAD_X, y0), "正しいタンブリングを、", font=title_f, fill=PURPLE_DARK)
    _, lh = measure_text(d, "正しいタンブリングを、", title_f)
    y = y0 + lh + mm(2)
    d.text((PAD_X, y), "安全に、段階的に。", font=title_f, fill=PURPLE_DARK)
    y += lh + mm(4)
    sub_f = font(15)
    d.text((PAD_X, y), "指導者・選手・保護者のための、タンブリング教科書アプリ。",
           font=sub_f, fill=TEXT_DARK)
    y += mm(11)
    # 数字バー
    stats = [
        ("33", "技"),
        ("44", "トレーニング"),
        ("105", "解説動画"),
        ("Lv1〜Lv6", "段階別ロードマップ"),
    ]
    bar_h = mm(24)
    bar_x0, bar_x1 = PAD_X, mm(W_MM) - PAD_X
    bar_w = bar_x1 - bar_x0
    bar_img = Image.new("RGB", (bar_w, bar_h))
    gradient_rect(bar_img, (0, 0, bar_w, bar_h), PURPLE_DARK, PINK, "horizontal")
    mask = Image.new("L", (bar_w, bar_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, bar_w, bar_h), radius=mm(4), fill=255)
    canvas.paste(bar_img, (bar_x0, y), mask)
    seg_w = bar_w / 4
    for i, (num, label) in enumerate(stats):
        sx0 = bar_x0 + int(i * seg_w)
        sx1 = bar_x0 + int((i + 1) * seg_w)
        num_f = font(28 if i < 3 else 14, bold=True)
        text_centered(d, (sx0, y + mm(3), sx1, y + mm(15)), num, num_f, WHITE)
        label_f = font(11)
        text_centered(d, (sx0, y + mm(15), sx1, y + bar_h - mm(1)), label, label_f, WHITE)
    y += bar_h + mm(4)
    # 完全無料帯
    free_h = mm(13)
    free_img = Image.new("RGB", (bar_w, free_h))
    gradient_rect(free_img, (0, 0, bar_w, free_h), (255, 235, 60), (255, 200, 30), "horizontal")
    fm = Image.new("L", (bar_w, free_h), 0)
    ImageDraw.Draw(fm).rounded_rectangle((0, 0, bar_w, free_h), radius=mm(3), fill=255)
    canvas.paste(free_img, (bar_x0, y), fm)
    box_w = mm(30)
    d.rounded_rectangle((bar_x0 + mm(3), y + mm(1.5), bar_x0 + mm(3) + box_w, y + free_h - mm(1.5)),
                        radius=mm(2), fill=(45, 30, 70))
    text_centered(d, (bar_x0 + mm(3), y, bar_x0 + mm(3) + box_w, y + free_h),
                  "完全無料", font(15, bold=True), (255, 235, 60))
    d.text((bar_x0 + mm(3) + box_w + mm(5), y + mm(2)),
           "動画105本の閲覧／トレーニングメニュー作成／成長記録 すべて無料！",
           font=font(13, bold=True), fill=(45, 30, 70))
    d.text((bar_x0 + mm(3) + box_w + mm(5), y + mm(7.5)),
           "アカウント登録ナシでも、すぐに使えます。", font=font(10), fill=(80, 60, 110))
    return y + free_h + mm(6)


def draw_three_targets(canvas, y0):
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ 3者すべてに、効く。", font=font(15, bold=True), fill=DARK_TEXT)
    y = y0 + mm(9)
    inner_w = mm(W_MM) - PAD_X * 2
    col_w = (inner_w - mm(6)) // 3
    section_h = mm(34)
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
        cx0 = PAD_X + i * (col_w + mm(3))
        cx1 = cx0 + col_w
        cy0 = y
        cy1 = cy0 + section_h
        rounded_rect(d, (cx0, cy0, cx1, cy1), mm(3), fill=WHITE, outline=GRAY_BORDER, width=1)
        # サイドバー
        side_img = Image.new("RGB", (mm(5), section_h))
        gradient_rect(side_img, (0, 0, mm(5), section_h), color, color, "vertical")
        side_mask = Image.new("L", (mm(5), section_h), 0)
        ImageDraw.Draw(side_mask).rounded_rectangle((0, 0, mm(5), section_h), radius=mm(3), fill=255)
        canvas.paste(side_img, (cx0, cy0), side_mask)
        # 番号バッジ
        num_str = ["①", "②", "③"][i]
        d.rounded_rectangle(
            (cx0 + mm(8), cy0 + mm(3), cx0 + mm(14), cy0 + mm(10)),
            radius=mm(1.5), fill=color)
        text_centered(d, (cx0 + mm(8), cy0 + mm(3), cx0 + mm(14), cy0 + mm(10)),
                      num_str, font(12, bold=True), WHITE)
        d.text((cx0 + mm(16), cy0 + mm(3.5)),
               f"{audience}{suffix}", font=font(14, bold=True), fill=DARK_TEXT)
        # bullets
        by = cy0 + mm(14)
        for b in bullets:
            d.text((cx0 + mm(9), by), "・" + b, font=font(11), fill=TEXT_DARK)
            by += mm(7)
    return y + section_h + mm(6)


def draw_highlight(canvas, y0):
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ コーチの仕事を、半分に。（目玉機能）",
           font=font(15, bold=True), fill=DARK_TEXT)
    y = y0 + mm(9)
    inner_w = mm(W_MM) - PAD_X * 2
    col_w = (inner_w - mm(6)) // 2
    sec_h = mm(55)
    items = [
        {
            "badge": "★目玉 #1  コーチ向け",
            "title": "練習プログラム自動生成→指導配置図",
            "desc": "人数・目標技を入れれば、安全なサーキット配置図を自動描画。",
            "img": SHOTS / "desktop" / "01_program_circuit.png",
            "color": PURPLE,
        },
        {
            "badge": "★目玉 #2  コーチ向け",
            "title": "選手全員の進捗をヒートマップで一望",
            "desc": "達成率・あと少し・練習中を色分け。次に伸ばす選手が一目で。",
            "img": SHOTS / "desktop" / "02_progress_heatmap.png",
            "color": CYAN,
        },
    ]
    for i, item in enumerate(items):
        cx0 = PAD_X + i * (col_w + mm(6))
        cx1 = cx0 + col_w
        cy0 = y
        cy1 = cy0 + sec_h
        rounded_rect(d, (cx0, cy0, cx1, cy1), mm(3), fill=DARK_BG_2, outline=item["color"], width=3)
        # スクショ
        img_h = mm(32)
        paste_screenshot(canvas, str(item["img"]),
                         (cx0 + mm(3), cy0 + mm(3), cx1 - mm(3), cy0 + mm(3) + img_h),
                         radius_mm=2)
        # バッジ
        ty = cy0 + mm(3) + img_h + mm(3)
        bw, _ = measure_text(d, item["badge"], font(10, bold=True))
        d.rounded_rectangle((cx0 + mm(4), ty, cx0 + mm(4) + bw + mm(5), ty + mm(7)),
                            radius=mm(1.5), fill=item["color"])
        d.text((cx0 + mm(6.5), ty + mm(1)), item["badge"], font=font(10, bold=True), fill=WHITE)
        ty += mm(10)
        d.text((cx0 + mm(4), ty), item["title"], font=font(12, bold=True), fill=WHITE)
        ty += mm(6)
        # 説明（折返し）
        max_chars = 30
        lines = []
        cur = ""
        for ch in item["desc"]:
            cur += ch
            if len(cur) >= max_chars:
                lines.append(cur); cur = ""
        if cur: lines.append(cur)
        for ln in lines[:2]:
            d.text((cx0 + mm(4), ty), ln, font=font(10), fill=(220, 215, 240))
            ty += mm(5)
    return y + sec_h + mm(6)


def draw_updates(canvas, y0):
    """最新アップデート 6カード（2x3）"""
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ 最新アップデート",
           font=font(15, bold=True), fill=DARK_TEXT)
    y = y0 + mm(9)
    inner_w = mm(W_MM) - PAD_X * 2
    col_w = (inner_w - mm(6)) // 3
    row_h = mm(19)
    items = [
        ("練習ストリーク報酬", "30日連続で有料動画1本を永続アンロック", (255, 138, 61)),
        ("携帯で1画面ぜんぶ", "アコーディオン式、開閉状態を自動記憶", CYAN),
        ("コーチに新着通知", "LINE風赤バッジで未確認提出を即通知", PINK),
        ("動画105本に拡張", "側転1/4・ハンドスプリング等の新規動画", GREEN),
        ("Lv1〜Lv6 段階別", "各技にレベルタグを表示", PURPLE),
        ("名称・分類の整理", "現場で使いやすい呼称に全面整理", GOLD),
    ]
    for i, (title, body, color) in enumerate(items):
        col = i % 3
        row = i // 3
        cx0 = PAD_X + col * (col_w + mm(3))
        cy0 = y + row * (row_h + mm(3))
        rounded_rect(d, (cx0, cy0, cx0 + col_w, cy0 + row_h),
                     mm(2), fill=WHITE, outline=color, width=2)
        d.text((cx0 + mm(3), cy0 + mm(3)), title, font=font(11, bold=True), fill=DARK_TEXT)
        # 説明（折返し）
        max_chars = 22
        lines = []
        cur = ""
        for ch in body:
            cur += ch
            if len(cur) >= max_chars:
                lines.append(cur); cur = ""
        if cur: lines.append(cur)
        by = cy0 + mm(10)
        for ln in lines[:2]:
            d.text((cx0 + mm(3), by), ln, font=font(9), fill=TEXT_MUTED)
            by += mm(4.5)
    return y + row_h * 2 + mm(3) + mm(6)


def draw_steps(canvas, y0):
    """3ステップで始められます"""
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ 3ステップで始められます",
           font=font(15, bold=True), fill=DARK_TEXT)
    y = y0 + mm(9)
    inner_w = mm(W_MM) - PAD_X * 2
    col_w = (inner_w - mm(6)) // 3
    row_h = mm(21)
    steps = [
        ("1", "QR をスキャン", "スマホのカメラで読み取り、Webアプリを起動"),
        ("2", "ホーム画面に追加", "Safari / Chrome で共有 → 追加でアプリ化"),
        ("3", "選手 or コーチで始める", "無料プランでも動画・トレメ・記録が使える"),
    ]
    for i, (num, title, desc) in enumerate(steps):
        cx0 = PAD_X + i * (col_w + mm(3))
        cy0 = y
        rounded_rect(d, (cx0, cy0, cx0 + col_w, cy0 + row_h),
                     mm(2.5), fill=BG_PURPLE_SOFT, outline=PURPLE, width=1)
        # 番号
        d.ellipse((cx0 + mm(4), cy0 + mm(4), cx0 + mm(14), cy0 + mm(14)), fill=PURPLE)
        text_centered(d, (cx0 + mm(4), cy0 + mm(4), cx0 + mm(14), cy0 + mm(14)),
                      num, font(14, bold=True), WHITE)
        d.text((cx0 + mm(18), cy0 + mm(5)), title, font=font(11, bold=True), fill=DARK_TEXT)
        # 説明（折返し）
        max_chars = 18
        lines = []
        cur = ""
        for ch in desc:
            cur += ch
            if len(cur) >= max_chars:
                lines.append(cur); cur = ""
        if cur: lines.append(cur)
        by = cy0 + mm(16)
        for ln in lines[:2]:
            d.text((cx0 + mm(4), by), ln, font=font(9), fill=TEXT_MUTED)
            by += mm(4.5)
    return y + row_h + mm(6)


def draw_pricing(canvas, y0):
    d = ImageDraw.Draw(canvas)
    d.text((PAD_X, y0), "▸ プラン（既存4 + 新2）",
           font=font(15, bold=True), fill=DARK_TEXT)
    y = y0 + mm(9)
    inner_w = mm(W_MM) - PAD_X * 2

    existing = [
        ("フリー", "¥0/月", "動画105本・トレメ・記録すべて無料", (255, 200, 30), True),
        ("個人", "¥480/月", "プレミアム動画も解放", PURPLE, False),
        ("コーチ", "¥1,200/月", "教室主宰（〜10名）", PURPLE, False),
        ("コーチプラス", "¥1,980/月", "大規模チーム 無制限", PURPLE, False),
    ]
    ex_col_w = (inner_w - mm(3) * 3) // 4
    ex_h = mm(17)
    for i, (name, price, desc, color, hi) in enumerate(existing):
        cx0 = PAD_X + i * (ex_col_w + mm(3))
        cx1 = cx0 + ex_col_w
        if hi:
            rounded_rect(d, (cx0, y, cx1, y + ex_h), mm(2),
                         fill=(255, 248, 200), outline=(255, 200, 30), width=2)
            d.text((cx0 + mm(2.5), y + mm(1.5)), name, font=font(11, bold=True), fill=(140, 100, 0))
            d.text((cx0 + mm(2.5), y + mm(6)), price, font=font(14, bold=True), fill=(180, 130, 0))
            d.text((cx0 + mm(2.5), y + mm(14)), desc, font=font(8), fill=(120, 90, 0))
        else:
            rounded_rect(d, (cx0, y, cx1, y + ex_h), mm(2),
                         fill=BG_PURPLE_SOFT, outline=BORDER, width=1)
            d.text((cx0 + mm(2.5), y + mm(1.5)), name, font=font(10, bold=True), fill=DARK_TEXT)
            d.text((cx0 + mm(2.5), y + mm(6)), price, font=font(13, bold=True), fill=color)
            d.text((cx0 + mm(2.5), y + mm(14)), desc, font=font(8), fill=TEXT_MUTED)
    y += ex_h + mm(4)

    # 新規2プラン（強調）
    new_h = mm(15)
    new_w = (inner_w - mm(6)) // 2
    new_plans = [
        {
            "name": "トレーニング指導 NEW",
            "price": "¥4,500/月",
            "subtitle": "個別メニュー作成・動画添削月20本",
            "color_a": ORANGE, "color_b": ORANGE_DARK,
        },
        {
            "name": "完全1on1 NEW",
            "price": "¥7,500/月",
            "subtitle": "動画添削無制限・専用LINE・月1通話",
            "color_a": PINK, "color_b": PURPLE_DARK,
        },
    ]
    for i, plan in enumerate(new_plans):
        cx0 = PAD_X + i * (new_w + mm(6))
        cx1 = cx0 + new_w
        bg = Image.new("RGB", (new_w, new_h))
        gradient_rect(bg, (0, 0, new_w, new_h), plan["color_a"], plan["color_b"], "diag")
        mask = Image.new("L", (new_w, new_h), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, new_w, new_h), radius=mm(2.5), fill=255)
        canvas.paste(bg, (cx0, y), mask)
        d.text((cx0 + mm(3), y + mm(2)), plan["name"], font=font(11, bold=True), fill=WHITE)
        d.text((cx0 + mm(3), y + mm(8)), plan["price"], font=font(18, bold=True), fill=WHITE)
        d.text((cx0 + mm(3), y + mm(16.5)), plan["subtitle"], font=font(9), fill=WHITE)
    y += new_h + mm(2)
    d.text((PAD_X, y), "※ 新サブスク2種は先行受付中・準備中（協会法人登記完了後に開始）",
           font=font(8), fill=TEXT_MUTED)
    return y + mm(5)


def draw_footer(canvas, y0):
    d = ImageDraw.Draw(canvas)
    inner_w = mm(W_MM) - PAD_X * 2

    # CTA帯
    cta_h = mm(13)
    cta_img = Image.new("RGB", (inner_w, cta_h))
    gradient_rect(cta_img, (0, 0, inner_w, cta_h), PINK, PURPLE_DARK, "horizontal")
    mask = Image.new("L", (inner_w, cta_h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, inner_w, cta_h), radius=mm(3), fill=255)
    canvas.paste(cta_img, (PAD_X, y0), mask)
    text_centered(d, (PAD_X, y0, PAD_X + inner_w, y0 + cta_h - mm(5)),
                  "▶ 今すぐ無料で始める",
                  font(20, bold=True), WHITE)
    text_centered(d, (PAD_X, y0 + cta_h - mm(6), PAD_X + inner_w, y0 + cta_h),
                  "（動画閲覧・トレーニングメニュー作成・成長記録 まるごと無料）",
                  font(11), (255, 235, 200))
    y = y0 + cta_h + mm(4)

    # QR + 情報
    qr_size = mm(40)
    qr_path = OUT_DIR / "_promo_qr.png"
    gen_qr_png_hi("https://roadmap.cheer-tumbling.jp/", str(qr_path))
    draw_qr_box(canvas, (PAD_X, y, PAD_X + qr_size, y + qr_size), str(qr_path))
    # 右側
    tx = PAD_X + qr_size + mm(6)
    d.text((tx, y + mm(1)), "QRをスキャン or 直接アクセス", font=font(13, bold=True), fill=DARK_TEXT)
    d.text((tx, y + mm(9)), "roadmap.cheer-tumbling.jp", font=font(17, bold=True), fill=PURPLE_DARK)
    d.text((tx, y + mm(20)), "iPhone: Safari ／ Android: Chrome  ／  クレジット登録なし", font=font(9), fill=TEXT_MUTED)
    d.text((tx, y + mm(26)), "監修：中村 祐介（指導歴18年・元体操選手）", font=font(9), fill=TEXT_MUTED)
    d.text((tx, y + mm(31)), "　　　前島 一貴（国際ライセンス保有）", font=font(9), fill=TEXT_MUTED)
    d.text((tx, y + mm(38)), "発行：一般社団法人 チアタンブリング協会", font=font(8), fill=TEXT_MUTED)


def make_poster():
    img = make_canvas(W_MM, H_MM)
    y = mm(8)
    y = draw_header(img, y)
    y = draw_hero(img, y)
    y = draw_three_targets(img, y)
    y = draw_highlight(img, y)
    y = draw_updates(img, y)
    y = draw_steps(img, y)
    y = draw_pricing(img, y)
    # footer は下端に固定（切れ防止・QR確保）
    FOOTER_H_MM = 58  # CTA 13 + gap 4 + QR 40 + 監修情報 + 余白
    footer_y = mm(H_MM - FOOTER_H_MM)
    # pricing 終了位置が footer 開始より下だったら白マスクで pricing 部分を消去
    if y > footer_y - mm(2):
        # 重なり部分を白塗りしてクリア
        from PIL import ImageDraw as _ID
        _ID.Draw(img).rectangle((0, footer_y - mm(2), mm(W_MM), footer_y), fill=(250, 245, 255))
    draw_footer(img, footer_y)

    out_png = OUT_DIR / "promo_a3_poster.png"
    out_pdf = OUT_DIR / "promo_a3_poster.pdf"
    img.save(out_png, "PNG", dpi=(DPI, DPI))
    img.save(out_pdf, "PDF", resolution=DPI)
    print(f"✓ {out_png}")
    print(f"✓ {out_pdf}")


if __name__ == "__main__":
    make_poster()
