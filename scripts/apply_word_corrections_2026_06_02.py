#!/usr/bin/env python3
"""
2026-06-02 Word修正コメントを cheer_tumbling_skills.json に適用するスクリプト。
監督が Word で送ってきた修正コメントを一括反映する。
backup は backup-2026-06-02-pre-word-corrections/ にある。
"""
import json
import sys
from pathlib import Path

JSON_PATH = Path(__file__).parent.parent / 'data' / 'cheer_tumbling_skills.json'

def load():
    return json.loads(JSON_PATH.read_text(encoding='utf-8'))

def save(d):
    JSON_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

def get_skill(d, sid):
    s = next((x for x in d['skills'] if x['id'] == sid), None)
    if not s:
        raise ValueError(f'Skill not found: {sid}')
    return s

def find_idx(items, title):
    for i, it in enumerate(items):
        if it['title'] == title:
            return i
    raise ValueError(f'Item not found: {title}')

def replace(items, old_title, new_title, new_detail=None):
    """title が old_title のアイテムを差し替え。new_detail が None なら detail はそのまま。"""
    i = find_idx(items, old_title)
    items[i]['title'] = new_title
    if new_detail is not None:
        items[i]['detail'] = new_detail

def replace_detail(items, title, new_detail):
    """title はそのまま、detail だけ差し替え。"""
    i = find_idx(items, title)
    items[i]['detail'] = new_detail

def delete(items, title):
    i = find_idx(items, title)
    items.pop(i)

def add(items, title, detail):
    items.append({'title': title, 'detail': detail})

def reorder(items, new_titles_order):
    by_title = {it['title']: it for it in items}
    items.clear()
    for t in new_titles_order:
        items.append(by_title[t])


def main():
    d = load()

    # ============================================================
    # バニーホップ (bunny_hop)
    # ============================================================
    s = get_skill(d, 'bunny_hop')
    s['description'] = (
        '両手を肩幅に先につき、お尻を高く上げて両足を胸に引きつけながらその場で跳ぶ運動です。'
        '腕で体重を支えて床を押す感覚を身につけ、ハンドスプリングやロンダートの「肩や腕で押す」'
        'という動きの土台になります。'
    )
    # points: '両手を肩幅より広めに着く' → '両手を肩幅に着く', '手と足を交互にリズムよく' 削除
    replace(s['points'], '両手を肩幅より広めに着く', '両手を肩幅に着く', '安定した支持基盤')
    delete(s['points'], '手と足を交互にリズムよく')
    # cautions: 'マットや柔らかい床で行う' → 'マットや床で行う'
    if any(c['title'] == 'マットや柔らかい床で行う' for c in s.get('cautions', [])):
        replace(s['cautions'], 'マットや柔らかい床で行う', 'マットや床で行う', '手首保護のため')
    # common_mistakes
    delete(s['common_mistakes'], '手足が同時に着く')
    delete(s['common_mistakes'], 'お尻が低い')
    replace_detail(s['common_mistakes'], '腰が曲がりすぎる', '体が潰れて勢いがなくなってしまう')
    replace_detail(s['common_mistakes'], '跳ぶ高さが低い', '腕で体重を支える強度が低くなってしまう')
    # progression: '小さなホップで前進' 削除、③④順番変更（残るのは「大きなホップで距離」「バニーホップ→倒立姿勢」「バニーホップ→前転」）
    delete(s['progression'], '小さなホップで前進')
    # 順番変更：現状は ['大きなホップで距離', 'バニーホップ→倒立姿勢', 'バニーホップ→前転']
    # Word doc は ③④の順番変更指示 → 'バニーホップ→倒立姿勢' と 'バニーホップ→前転' を入れ替え
    reorder(s['progression'], ['大きなホップで距離', 'バニーホップ→前転', 'バニーホップ→倒立姿勢'])

    # ============================================================
    # 背倒立 (shoulder_stand) — 応用練習・バリエーション 前後開脚 → 削除
    # ============================================================
    # JSON 側に variations はないが、関連スキル shoulder_stand_front_back_split がある。
    # 「応用練習・バリエーション」削除指示はそれを参照していると判断し、JSON 側で
    # メイン skill から切り離しはしない（バリエーション参照は HTML 側で管理）。
    # 注：HTMLの shoulder-stand スキルが variants を持っているか後で確認

    # ============================================================
    # ランジ姿勢 (lunge_position)
    # ============================================================
    s = get_skill(d, 'lunge_position')
    s['description'] = (
        '前足を深く沈めて膝を90度に曲げ、後ろ足を伸ばして上体を真っ直ぐ立てた前後開きの基本姿勢です。'
        '前方系のタンブリングのほとんどの始まりに使う構えで、'
        '前足の踏み込みから振り上げ脚へ力を伝える土台を作ります。'
    )
    # points: '上体は真っ直ぐ胸を張る' は points にあり
    if any(p['title'] == '上体は真っ直ぐ胸を張る' for p in s['points']):
        replace(s['points'], '上体は真っ直ぐ胸を張る', '後ろ足のかかとを浮かす', '足を大きく前後に開く')
    # cautions: '上体が前に倒れない' は cautions にあり（JSON 構造上）
    if any(c['title'] == '上体が前に倒れない' for c in s.get('cautions', [])):
        replace(s['cautions'], '上体が前に倒れない', '上体を前に倒し過ぎない', '姿勢の崩れに注意')
    # progression: '左右交互に10回×3セット' 削除
    if any(p['title'] == '左右交互に10回×3セット' for p in s['progression']):
        delete(s['progression'], '左右交互に10回×3セット')
    elif any(p['title'] == '左右交互に10回 × 3セット' for p in s['progression']):
        delete(s['progression'], '左右交互に10回 × 3セット')

    # ============================================================
    # 壁倒立 (wall_handstand)
    # ============================================================
    s = get_skill(d, 'wall_handstand')
    s['description'] = (
        '壁に背中側またはお腹を向けて倒立をキープする練習です。'
        'バランスを取る不安を、壁を使うことで肩まわりで床を押す力とお腹まわりを締める力という'
        '倒立の中心だけを集中して鍛えられます。'
        '振り上げ倒立などの前段階となる重要な練習です。'
    )
    # cautions
    replace(s['cautions'], '必ず補助者をつける', '初心者は補助者をつける', '倒れる可能性のある方向を支えてもらう')
    # common_mistakes
    replace(s['common_mistakes'], '肩が開かず背中で支える', '肩が開かず身体を反って支える', '肩で押す意識が足りない')
    # progression
    replace(s['progression'], '壁を背に足を登らせる', '壁にお腹を向けて足で壁を登る', '上下逆さま姿勢に慣れる')
    delete(s['progression'], '壁を正面にして30秒キープ')
    replace(s['progression'], '壁で肩タップ', '壁にお腹を向けて肩タップ', '片手ずつ手を離して押す感覚を養う')

    # ============================================================
    # 振り上げ倒立 (kick_up_handstand)
    # ============================================================
    s = get_skill(d, 'kick_up_handstand')
    # cautions
    replace(s['cautions'], '必ず補助者をつける', '初心者は補助者をつける', '倒れる可能性のある方向を支えてもらう')
    if any(c['title'] == 'ランジ→振り上げで壁倒立' for c in s['cautions']):
        delete(s['cautions'], 'ランジ→振り上げで壁倒立')
    # progression
    if any(p['title'] == '自由倒立を2秒キープ' for p in s['progression']):
        replace(s['progression'], '自由倒立を2秒キープ', '壁を使わず自立倒立を2秒キープ', '壁から離れて実施')
    if any(p['title'] == '倒立→横に降りる' for p in s['progression']):
        delete(s['progression'], '倒立→横に降りる')

    # ============================================================
    # ブリッジ (bridge)
    # ============================================================
    s = get_skill(d, 'bridge')
    # points
    if any(p['title'] == '腕を伸ばし肩を入れる' for p in s['points']):
        replace_detail(s['points'], '腕を伸ばし肩を入れる', '肩を手首の上にくるようにする')
    if any(p['title'] == '足は腰幅でつま先前' for p in s['points']):
        replace(s['points'], '足は腰幅でつま先前', '足は肩幅', 'つま先を真っ直ぐに')
    if any(c['title'] == '硬い床では行わない' for c in s.get('cautions', [])):
        replace(s['cautions'], '硬い床では行わない', '表面が硬い床では行わない', '必ずマットの上で行う')
    # common_mistakes
    if any(m['title'] == '頭が下がる' for m in s['common_mistakes']):
        replace_detail(s['common_mistakes'], '頭が下がる', '肩で押せていない')
    # progression
    if any(p['title'] == '立位からブリッジ降り' for p in s['progression']):
        replace(
            s['progression'], '立位からブリッジ降り', '立位からブリッジ降り',
            'エバーマット（柔らかいマット）を身体の後ろに置いて練習する'
        )

    # ============================================================
    # 膝ブリッジ (kneeling_backbend)
    # ============================================================
    s = get_skill(d, 'kneeling_backbend')
    s['description'] = (
        '膝立ちの姿勢から腕を耳の後ろに上げ、ゆっくり後方に反って指を軽く床につけて、'
        'ブリッジ姿勢から膝立ちの姿勢に戻ってくる技です。'
        '寝た姿勢と立位ブリッジの中間段階で、後ろに倒れる怖さを少しずつ克服する心の橋渡しになります。'
    )
    # points
    if any(p['title'] == '膝は腰幅でつま先を立てる' for p in s['points']):
        replace(
            s['points'], '膝は腰幅でつま先を立てる',
            '膝は肩幅で準備（膝と膝の間に拳二つ分のスペースを作る）', '安定した土台'
        )
    if any(p['title'] == '腕を耳の横に伸ばす' for p in s['points']):
        replace(s['points'], '腕を耳の横に伸ばす', '腕を耳の後ろに伸ばす', '降ろす前の構え')
    if any(p['title'] == 'ゆっくり手を床に降ろす' for p in s['points']):
        replace_detail(s['points'], 'ゆっくり手を床に降ろす', '同じスピードを保ち続ける')
    # common_mistakes
    if any(m['title'] == '視線が下を向く' for m in s['common_mistakes']):
        replace_detail(s['common_mistakes'], '視線が下を向く', '身体が丸まり、ブリッジの形が成立しない')
    # progression
    if any(p['title'] == 'スムーズに連続実施' for p in s['progression']):
        replace_detail(s['progression'], 'スムーズに連続実施', '自力で正しく5回ほど繰り返す')

    # ============================================================
    # 前転 (forward_roll)
    # ============================================================
    s = get_skill(d, 'forward_roll')
    replace_detail(s['points'], 'おへそを見て背中を丸める', 'ボールのような形をキープする')
    replace(s['points'], '手は体重を支えるだけ', '腕で体重を支えながら回る', '肘を曲げながら後頭部を接地させる')
    replace_detail(s['points'], '立ち上がりで前重心を作る', '両手を前に伸ばす')
    replace_detail(s['progression'], 'だんごむしの形をキープ', '30秒静止できるようにする')

    # ============================================================
    # 後転 (backward_roll)
    # ============================================================
    s = get_skill(d, 'backward_roll')
    s['description'] = (
        '後方に転がりながら、手のひらで床を押して頭を抜く、後ろまわりの入門技です。'
        '「後ろに移動する」感覚と「腕で押して頭を守る」動作を同時に学び、'
        'ここでの腕の押しが後転倒立やバク転の押す動きに直接つながります。'
    )
    if any(p['title'] == '回り終わりに膝立ちか立ち' for p in s['points']):
        replace(
            s['points'], '回り終わりに膝立ちか立ち',
            'つま先から着いて足から着地する', '膝を着かずに床を押す'
        )
    if any(p['title'] == '坂マットで後転' for p in s['progression']):
        replace_detail(s['progression'], '坂マットで後転', 'スピードを利用して回転する')
    if any(p['title'] == '平らな場所で立位→後転' for p in s['progression']):
        replace_detail(s['progression'], '平らな場所で立位→後転', 'しゃがみの姿勢で完成')

    # ============================================================
    # 側転 (cartwheel)
    # ============================================================
    s = get_skill(d, 'cartwheel')
    s['description'] = (
        '横方向に倒立を通って「手・手・足・足」の順で一直線に揃えて着地する回転技です。'
        '腰を高く上げて倒立を通す。'
        'ここを省くとロンダートや側宙で必要な高さと回転の勢いが作りにくくなります。'
    )
    replace(s['points'], '二本目の手は遠くに', '手は遠くに着く', '前に進む勢いを持続させる')
    # cautions: '左右両方を必ず練習' → 削除
    if any(c['title'] == '左右両方を必ず練習' for c in s.get('cautions', [])):
        delete(s['cautions'], '左右両方を必ず練習')
    # common_mistakes
    replace(
        s['common_mistakes'], '手と足が同じ位置',
        '手と足が同じ近い', '前に進む勢いが持続させれない'
    )
    delete(s['common_mistakes'], '片側ばかり練習する')
    # progression
    replace(s['progression'], 'ライン上で倒立→横に降ろす', 'ライン上で側転', '通過点の感覚作り')
    replace_detail(s['progression'], 'ゆっくり大きい側転', 'スピードをコントロールする意識で実施')
    # variants 系：旧 'スピードを上げる' を 'スピードを変える(速い、遅い)' に
    if any(p['title'] == 'スピードを上げる' for p in s['progression']):
        replace(
            s['progression'], 'スピードを上げる',
            'スピードを変える（速い、遅い）', 'スピードのコントロールをする'
        )

    # ============================================================
    # 後転倒立 (back_extension_roll)
    # ============================================================
    s = get_skill(d, 'back_extension_roll')
    s['name_en'] = 'Backward roll to handstand'
    if any(c['title'] == '手の構えを忘れない' for c in s.get('cautions', [])):
        replace_detail(s['cautions'], '手の構えを忘れない', '途中で出すと遅れて力が伝わらない')
    if any(c['title'] == '無理せず前転で逃げる' for c in s.get('cautions', [])):
        replace(s['cautions'], '無理せず前転で逃げる', '力を抜かず前転に戻る', '倒立まで行けない時の対処')
    if any(m['title'] == 'あごを引きすぎる' for m in s['common_mistakes']):
        replace(s['common_mistakes'], 'あごを引きすぎる', '床を見るのが遅い', '倒立で押す時に方向が正確にならない')
    if any(p['title'] == '坂を使った後転倒立' for p in s['progression']):
        replace(s['progression'], '坂を使った後転倒立', '段差を使った後転倒立', '勢いをつけやすい環境で練習')

    # ============================================================
    # 倒立前転 (handstand_forward_roll)
    # ============================================================
    s = get_skill(d, 'handstand_forward_roll')
    if any(p['title'] == '肘をゆっくり曲げる' for p in s['points']):
        replace_detail(s['points'], '肘をゆっくり曲げる', '一気に下ろさず力を使いながら下げる')
    if any(p['title'] == '頭頂部をマットにつける' for p in s['points']):
        replace(s['points'], '頭頂部をマットにつける', '後頭部をマットにつける', '頭頂部にならないよう注意')
    if any(m['title'] == '頭から落ちてしまう' for m in s['common_mistakes']):
        replace_detail(s['common_mistakes'], '頭から落ちてしまう', '腕の力を入れ続けていないことが主な原因')
    if any(p['title'] == 'カエル倒立から前転' for p in s['progression']):
        replace(s['progression'], 'カエル倒立から前転', 'バニーホップから前転', '低い位置で感覚をつかむ')

    # ============================================================
    # ブリッジキックオーバー (bridge_kickover)
    # ============================================================
    s = get_skill(d, 'bridge_kickover')
    if any(p['title'] == '一瞬倒立を通過する' for p in s['points']):
        replace(s['points'], '一瞬倒立を通過する', '一瞬倒立前後開脚を通過する', '垂直軸を通す意識')
    if any(p['title'] == 'かかとから着地し体の前へ' for p in s['points']):
        replace(s['points'], 'かかとから着地し体の前へ', 'つま先から着地し体の前へ', '制御を保ち続ける')
    if any(p['title'] == '坂マット上でキックオーバー' for p in s['progression']):
        replace(
            s['progression'], '坂マット上でキックオーバー',
            '20-30cmのエバーマットからキックオーバー', '高さを利用して強度を下げる'
        )

    # ============================================================
    # 立位ブリッジ〜起き上がり (standing_bridge_with_standup)
    # ============================================================
    s = get_skill(d, 'standing_bridge_with_standup')
    s['description'] = (
        '立った姿勢から腕を耳の後ろに上げてゆっくり後方に動かし、ブリッジを通って手で押して、'
        '立ち上がるまでをひとつの動きで行う動作です。'
        '後方ウォークオーバーやバク転で必要な「後ろに体をあずける怖さ」を乗り越える大切なステップです。'
    )
    if any(p['title'] == '腕を耳の横に上げて後方へ' for p in s['points']):
        replace(s['points'], '腕を耳の横に上げて後方へ', '腕を耳の後ろに上げて後方へ', 'ゆっくり動かす')
    if any(p['title'] == '足で床を蹴り体重を前に' for p in s['points']):
        replace(s['points'], '足で床を蹴り体重を前に', '軽く膝を曲げて体重を前に移動する', '同じスピードで立ち上がる')
    if any(p['title'] == '壁を使って後方に手を降ろす' for p in s['progression']):
        replace(s['progression'], '壁を使って後方に手を降ろす', 'エバーマットを使って後方に手を降ろす', 'マットを支えに練習')

    # ============================================================
    # 前方ウォークオーバー (front_walkover)
    # ============================================================
    s = get_skill(d, 'front_walkover')
    s['description'] = (
        '振り上げ脚を高く上げて倒立前後開脚を通過し、ブリッジを経由しながら片足ずつ着地して立ち上がる、'
        '前方系の技です。前後開脚の柔軟性を実際の技に変える動きで、'
        'ハンドスプリングや前方エアリアルの基礎感覚作りに繋がります。'
    )
    if any(p['title'] == '一本目の着地で立ち上がる勢い' for p in s['points']):
        replace(
            s['points'], '一本目の着地で立ち上がる勢い',
            '一本目の足の着地で体重移動をする', '重心を前に運ぶ'
        )
    if any(p['title'] == '両足同時着地' for p in s['points']):
        replace(s['points'], '両足同時着地', '倒立〜ブリッジで着地', 'ゆっくりコントロール')
    if any(m['title'] == '柔軟性不足で背中で止まる' for m in s.get('common_mistakes', [])):
        replace(
            s['common_mistakes'], '柔軟性不足で背中で止まる',
            '柔軟性不足で背中で真っ直ぐ', '胸を開く動作を鍛える'
        )
    if any(p['title'] == '坂マットでウォークオーバー' for p in s['progression']):
        replace(
            s['progression'], '坂マットでウォークオーバー',
            '5cmのマットの高さからウォークオーバー', '高さを利用して着地をして強度を下げる'
        )

    # ============================================================
    # 後方ウォークオーバー (back_walkover)
    # ============================================================
    s = get_skill(d, 'back_walkover')
    s['description'] = (
        '立った姿勢から振り上げ脚を真上に上げて後ろに反り、'
        '片足を上げたブリッジ手を通過して回って立ち上がる技です。'
        'バク転で必要な「肩から胸にかけて反らせる」「手と手の間を見続ける」感覚を、'
        'ゆっくりしたスピードで安全に身につけられる前段階になります。'
    )
    if any(p['title'] == '腕は耳の横、頭を腕の間に' for p in s['points']):
        replace(s['points'], '腕は耳の横、頭を腕の間に', '腕は耳の後ろ、頭を腕の間に', '目線で方向を作る')
    if any(p['title'] == '頭の位置を変えない' for p in s['points']):
        replace(
            s['points'], '頭の位置を変えない',
            '頭の位置が下がりすぎないように踏み込んだ足で上に跳ぶ', '逆さまになった時に視線は真下'
        )
    if any(c['title'] == '振り上げ脚の柔軟性を確保' for c in s.get('cautions', [])):
        replace_detail(s['cautions'], '振り上げ脚の柔軟性を確保', '前後開脚のイメージ')
    if any(m['title'] == '無意識に手を着く' for m in s['common_mistakes']):
        replace_detail(
            s['common_mistakes'], '無意識に手を着く',
            '跳んだ後に手を着くドリルの反復回数が多すぎると手を着く癖がつく可能性がある'
        )
    if any(m['title'] == '体が縦にならない' for m in s['common_mistakes']):
        replace(
            s['common_mistakes'], '体が縦にならない',
            'ゆがんで横に転倒する', '踏み込みの時に足が内側に入っている可能性がある'
        )
    if any(p['title'] == '片手側転→ノーハンドへ' for p in s['progression']):
        replace(s['progression'], '片手側転→ノーハンドへ', 'エバーマットを使用', 'ケガのリスクを軽減')

    # ============================================================
    # 前方エアリアル (front_aerial)
    # ============================================================
    s = get_skill(d, 'front_aerial')
    s['description'] = (
        '前方ウォークオーバーと同じ振り上げで入り、'
        '手を着かずに振り上げ脚を「真上ではなく前方」に大きく振り出して腰を回す技です。'
        '前後開脚の柔軟性を保ったまま空中で前回転を完成させる、'
        '脚力と柔軟性が必要となる技です。'
    )
    if any(p['title'] == 'ウォークオーバーと同じ振り上げ' for p in s['points']):
        replace(
            s['points'], 'ウォークオーバーと同じ振り上げ',
            'ウォークオーバーよりも素早い足の振り上げ', '基本動作の延長'
        )
    if any(p['title'] == '振り上げ脚を真上ではなく前方' for p in s['points']):
        replace(
            s['points'], '振り上げ脚を真上ではなく前方',
            '振り上げ脚を真上で止めずに回転を継続する', '上昇の中で回転力を生み出す'
        )
    if any(p['title'] == '一本目の足で確実に着地' for p in s['points']):
        replace_detail(s['points'], '一本目の足で確実に着地', '二本目は後からついてくる')
    if any(m['title'] == '振り上げが弱く手を着きそう' for m in s['common_mistakes']):
        replace(
            s['common_mistakes'], '振り上げが弱く手を着きそう',
            '足を振り上げるスピードが弱く失速', '回転が止まってしまう'
        )
    if any(m['title'] == '振り上げが真上になる' for m in s['common_mistakes']):
        replace(
            s['common_mistakes'], '振り上げが真上になる',
            '着地の時にアゴを引いて形が崩れる', '身体が丸まって着地が乱れる'
        )
    if any(p['title'] == 'ハイ・フロントウォークオーバー' for p in s['progression']):
        replace(
            s['progression'], 'ハイ・フロントウォークオーバー',
            '高速フロントウォークオーバー', '回転をかける'
        )
    if any(p['title'] == '連続で複数回' for p in s['progression']):
        delete(s['progression'], '連続で複数回')

    # ============================================================
    # バク転 (standing_back_handspring)
    # ============================================================
    s = get_skill(d, 'standing_back_handspring')
    s['description'] = (
        'その場から腕を前から振り上げて後方に飛び、両手で床を捉えて肩で押し、'
        '両足で着地する技です。腕の振り上げとつま先で床を蹴り続ける動きで、'
        '後方への移動と回転を同時に作り出します。後重心は床反力を打ち消すため厳禁です。'
    )
    if any(c['title'] == '椅子に座る後重心は厳禁' for c in s.get('cautions', [])):
        replace_detail(s['cautions'], '椅子に座る後重心は厳禁', '高さが出にくくなる')
    if any(m['title'] == '上に飛んでしまう' for m in s['common_mistakes']):
        replace(
            s['common_mistakes'], '上に飛んでしまう',
            '回転がかからずに上に飛んでしまう', '後方への移動距離が出ない'
        )
    if any(m['title'] == '腕の振りが弱い' for m in s['common_mistakes']):
        replace_detail(s['common_mistakes'], '腕の振りが弱い', '回転が作れない')
    if any(p['title'] == '補助付きで高い位置から' for p in s['progression']):
        replace(
            s['progression'], '補助付きで高い位置から',
            '補助付きでエバーマットを利用', '安全にできる環境で行う'
        )
    if any(p['title'] == 'バランスボール/トランポリン' for p in s['progression']):
        replace(
            s['progression'], 'バランスボール/トランポリン',
            'トランポリンを利用', '上昇する力を利用して正しい動作を習得'
        )
    if any(p['title'] == '完全自力で連続バク転' for p in s['progression']):
        replace(s['progression'], '完全自力で連続バク転', '自力でバク転', '正しく単発で実施')

    # ============================================================
    # ロンバク (round_off_back_handspring)
    # ============================================================
    s = get_skill(d, 'round_off_back_handspring')
    s['name'] = 'ロンダート〜バク転'
    s['description'] = (
        'ロンダートのリバウンドで床から足が離れる瞬間にバク転をつなげて、'
        'ロンダートで作った後方への勢いをそのまま使う連続技です。'
        '流れるように一つの動きにすることで、さらに加速をして'
        '宙返り系すべての連続技の基礎になります。'
    )
    if any(p['title'] == 'リバウンドの瞬間にバク転を始動' for p in s['points']):
        replace_detail(s['points'], 'リバウンドの瞬間にバク転を始動', '瞬間的に床を蹴る')
    if any(c['title'] == 'リズムを力で押し切らない' for c in s.get('cautions', [])):
        replace(
            s['cautions'], 'リズムを力で押し切らない',
            '各技で正しいポジションを確認する', 'リズムだけで行うと形が崩れやすい'
        )
    if any(m['title'] == 'リズムが合わず力で飛ぶ' for m in s['common_mistakes']):
        replace(
            s['common_mistakes'], 'リズムが合わず力で飛ぶ',
            '上体が起きず力で行う', 'タイミングが崩れる'
        )
    if any(p['title'] == 'ロンダート→ジャンプリバウンド' for p in s['progression']):
        replace(
            s['progression'], 'ロンダート→ジャンプリバウンド',
            'ロンダート〜後ろに歩く', '後方へ進む感覚をつける'
        )
    if any(p['title'] == '低速で通す' for p in s['progression']):
        replace_detail(s['progression'], '低速で通す', '動作を確認しながら実施')
        # title も '各技で止まる' に変更
        replace(
            s['progression'], '低速で通す' if any(p['title']=='低速で通す' for p in s['progression']) else '各技で止まる',
            '各技で止まる', '動作を確認しながら実施'
        )

    # ============================================================
    # 前方ハンドスプリング (front_handspring)
    # ============================================================
    s = get_skill(d, 'front_handspring')
    s['description'] = (
        '助走からホップで入り、手を前に着いて肩で床を強く押し返し、'
        '体を空中に運んで両足で着地する前方系の代表技です。'
        '腕で押すのではなく「肩で押す」感覚をつかむことがポイントで、'
        '肩のブロックが弱いとつぶれてヘッドスプリングに近い形になってしまいます。'
    )
    if any(p['title'] == '空中で体を反らせる' for p in s['points']):
        replace(
            s['points'], '空中で体を反らせる',
            '空中で体を反るイメージで背筋に力を入れる', '両足を揃えて着地'
        )
    if any(c['title'] == '倒立前転と前方ウォークオーバーが前提' for c in s.get('cautions', [])):
        replace(
            s['cautions'], '倒立前転と前方ウォークオーバーが前提',
            '倒立ブリッジと前方ウォークオーバーが前提', '基本必須'
        )
    if any(m['title'] == '肩のブロックが弱い' for m in s['common_mistakes']):
        replace_detail(s['common_mistakes'], '肩のブロックが弱い', '潰れて肘が曲がる')
    if any(m['title'] == '着地で膝が崩れる' for m in s['common_mistakes']):
        replace(
            s['common_mistakes'], '着地で膝が崩れる',
            '倒立姿勢で膝が曲がる', '後ろに倒れてしまう'
        )
    if any(m['title'] == '助走の勢いが弱い' for m in s['common_mistakes']):
        replace(
            s['common_mistakes'], '助走の勢いが弱い',
            '足を振り上げる勢いが弱い', '回りきれず途中で止まってしまう'
        )
    if any(m['title'] == '体が反らない' for m in s['common_mistakes']):
        replace(s['common_mistakes'], '体が反らない', '空中で力が入らない', '空中姿勢が作れない')

    # ============================================================
    # 側宙(エアリアル) (side_aerial)
    # ============================================================
    s = get_skill(d, 'side_aerial')
    s['description'] = (
        '側転と同じリズムで踏み切り、手を着かずに振り上げ脚の勢いと腕の振り込みだけで'
        '横方向に一回転する技です。空中で側転の形を完成させる必要があるため、'
        '完成度の高い側転が必要不可欠となります。'
    )
    if any(p['title'] == '側転と同じリズムで踏み切る' for p in s['points']):
        replace(
            s['points'], '側転と同じリズムで踏み切る',
            '側転と同じ動きが基本だが、上下の運動にするためにメリハリをつけて動かす',
            '基本動作の延長'
        )

    # ============================================================
    # ゆりかご (rocking) — nameEn のみ (JSON 側)
    # ============================================================
    s = get_skill(d, 'rocking')
    s['name_en'] = 'Rock & Roll'

    # ============================================================
    # 保存
    # ============================================================
    save(d)
    print(f'✅ 修正適用完了: {JSON_PATH}')
    print(f'   skills: {len(d["skills"])} 件')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'❌ エラー: {e}', file=sys.stderr)
        sys.exit(1)
