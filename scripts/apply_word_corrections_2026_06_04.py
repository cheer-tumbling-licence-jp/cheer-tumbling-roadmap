#!/usr/bin/env python3
"""
2026-06-04 Word修正コメント（Level 4,5,トレーニング一覧）適用スクリプト

監督指示の整理：
- トレーニング20件超の説明・ポイント変更
- 重要：ホロウホールド → 腹筋ゆりかごキープ、アーチホールド → 背筋キープ 等の改名
  → 各 skill の trainings 配列内の T() 呼び出しも連動して変更
- Level 4/5 の8技（スタンド宙返り、ロンダート バク宙、ロンバク バク宙、パンチフロント、
  レイアウト、フル、ウィップバック、ダブルフル、アラビアン）の description / points 等修正

実行方法:
    python3 scripts/apply_word_corrections_2026_06_04.py
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
HTML_PATH = ROOT / 'index.html'
JSON_PATH = ROOT / 'data' / 'cheer_tumbling_skills.json'


def patch_html(html, edits):
    """edits = [(old, new, description), ...] を順に適用"""
    for old, new, desc in edits:
        if old not in html:
            print(f'  ⚠️  not found: {desc}')
            continue
        if html.count(old) > 1:
            print(f'  ⚠️  multiple matches for: {desc} ({html.count(old)}件)')
        html = html.replace(old, new, 1)
        print(f'  ✓ {desc}')
    return html


def patch_html_all(html, old, new, desc):
    """全置換"""
    count = html.count(old)
    if count == 0:
        print(f'  ⚠️  not found (all): {desc}')
        return html
    html = html.replace(old, new)
    print(f'  ✓ {desc} ({count}件置換)')
    return html


def main():
    print('=== index.html を修正 ===')
    html = HTML_PATH.read_text(encoding='utf-8')

    # ============================================================
    # トレーニング配列内の修正
    # ============================================================

    edits = []

    # 上体起こし: points の呼吸 → お尻を浮かさない
    edits.append((
        "['反動を使わずお腹の力で起き上がる', '呼吸を止めない（息を吐きながら起きる）', '腰を反らさない', '首だけで起こさない']",
        "['反動を使わずお腹の力で起き上がる', 'お尻を浮かさない', '腰を反らさない', '首だけで起こさない']",
        '上体起こし points: 呼吸→お尻を浮かさない'
    ))

    # プランク: 呼吸 → 目線は斜め前
    edits.append((
        "['頭からかかとまで一直線に', 'お尻を上げ過ぎず・下げ過ぎず', '肩の真下に肘を置く', '呼吸を止めない']",
        "['頭からかかとまで一直線に', 'お尻を上げ過ぎず・下げ過ぎず', '肩の真下に肘を置く', '目線は斜め前']",
        'プランク points: 呼吸→目線斜め前'
    ))

    # サイドプランク: 左右バランスよく → 頭の向きも身体に合わせる
    edits.append((
        "['体を真横の一直線に', '腰が落ちないように', '肩の真下に肘', '左右バランスよく']",
        "['体を真横の一直線に', '腰が落ちないように', '肩の真下に肘', '頭の向きも身体に合わせる']",
        'サイドプランク points: 左右バランス→頭の向き'
    ))

    # ホロウホールド → 腹筋ゆりかごキープ（改名）
    edits.append((
        "id: 'hollow-hold', name: 'ホロウホールド', nameEn: 'Hollow Hold'",
        "id: 'hollow-hold', name: '腹筋ゆりかごキープ', nameEn: 'Hollow Hold'",
        'ホロウホールド → 腹筋ゆりかごキープ（trainings 配列）'
    ))
    # description 変更
    edits.append((
        "description: '体操でいちばん基本になるお腹まわりの姿勢です。すべての技で必要な「板みたいにまっすぐな体」を作ります。'",
        "description: '体操でいちばん基本になるお腹まわりの姿勢です。すべての技で必要な「背中を丸めた力強い姿勢」を作ります。'",
        '腹筋ゆりかごキープ description'
    ))
    # points: 緩いC字 → ディッシュ
    edits.append((
        "['腰を地面にしっかり押し付ける', 'お腹を凹ませて締める', '足と肩甲骨を浮かせる', '体は緩いC字（ホロウ）の形']",
        "['腰を地面にしっかり押し付ける', 'お腹を凹ませて締める', '足と肩甲骨を浮かせる', '身体はディッシュ（お皿）のような形']",
        '腹筋ゆりかごキープ points'
    ))

    # アーチホールド → 背筋キープ
    edits.append((
        "id: 'arch-hold', name: 'アーチホールド', nameEn: 'Arch Hold'",
        "id: 'arch-hold', name: '背筋キープ', nameEn: 'Arch Hold'",
        'アーチホールド → 背筋キープ（trainings 配列）'
    ))
    edits.append((
        "description: 'ホロウの反対の姿勢です。背中側の筋肉に同じ姿勢のまま力を入れて、バク転や宙返りで必要な「体の反り」を作ります。'",
        "description: '腹筋ゆりかごキープの反対の姿勢です。背中側の筋肉に同じ姿勢のまま力を入れて、バク転や宙返りで必要な「体の反り」を作ります。'",
        '背筋キープ description'
    ))
    edits.append((
        "['うつ伏せで腕と足を浮かせる', 'お尻と背中を締める', '頭は腕の間に挟む', '体全体を「反った棒」に']",
        "['うつ伏せで腕と足を浮かせる', 'お尻と背中を締める', '頭は腕の間に挟む', '全身で反って正しい「力の入れ方」を覚える']",
        '背筋キープ points'
    ))

    # V字腹筋: nameEn V-Up/V-Sit → V-snap
    edits.append((
        "id: 'v-sit', name: 'V字腹筋', nameEn: 'V-Up / V-Sit'",
        "id: 'v-sit', name: 'V字腹筋', nameEn: 'V-snap'",
        'V字腹筋 nameEn 変更'
    ))
    edits.append((
        "description: 'お腹の筋肉を一気に強く鍛える運動です。バク転やスタンド宙返りで足を引きつけるときに必要な、お腹のグッとこもる力を作ります。'",
        "description: 'お腹の筋肉を動的に一気に強く鍛える運動です。バク転やスタンド宙返りで瞬発的に足を引きつけるときに、必要な筋力を鍛えます。'",
        'V字腹筋 description'
    ))
    edits.append((
        "['上体と足を同時に持ち上げる', '体でV字を作る', '腰だけで動かさない', 'ゆっくり下ろす']",
        "['上体と足を同時に持ち上げる', '身体でV字を作る', '腕と耳をつけて行う', '素早く上げて下ろす']",
        'V字腹筋 points'
    ))

    # 背筋（バックエクステンション）
    edits.append((
        "description: '背中全体の力を鍛えるトレーニングです。ブリッジやバク転で必要な、体を反らせる力を作ります。'",
        "description: '背中全体の力を鍛えるトレーニングです。ブリッジやバク転で必要な、全身を使って身体を反らせる力を作ります。'",
        '背筋 description'
    ))
    edits.append((
        "['ゆっくり持ち上げる', '腰だけ反らせず、背中全体で', '反動を使わない', 'お尻も締める']",
        "['スピードをコントロールする', '腰だけ反らせず、腕を遠くに伸ばしながら行う', '反動を使わない', 'お尻も締める']",
        '背筋 points'
    ))

    # 腕立て伏せ
    edits.append((
        "description: '上半身全体を鍛える基本のトレーニングです。倒立やハンドスプリングで床を押すための力を作ります。',\n    points: ['体を一直線に保つ', '肘を体の横に開きすぎない', 'ゆっくり下ろし、力強く押し上げる', '呼吸を止めない']",
        "description: '上半身全体を鍛える基本のトレーニングです。倒立やハンドスプリングで床を押すための力を作ります。全ての技に必要な腕の筋力を鍛える基本かつ最も大切なトレーニングです。',\n    points: ['体を一直線に保つ', '手を肩幅より広めにつき、肘を横に曲げる', 'ゆっくり下ろし、力強く押し上げる', '前を向いてあご、腰は同じタイミングで床にタッチ']",
        '腕立て伏せ description+points'
    ))

    # パイクプッシュアップ
    edits.append((
        "description: 'おしりを高く上げた逆三角形の姿勢で行う腕立て伏せです。倒立で体を押し上げるときに必要な、肩まわりの力を作ります。',\n    points: ['お尻を高く上げ、頭を下げる', '肘を曲げて頭頂を地面に近づける', '肩で押す感覚', '腰を反らせない']",
        "description: 'おしりを高く上げた三角形の姿勢で行う腕立て伏せです。倒立で体を押し上げるときに必要な、肩まわりの力を作ります。',\n    points: ['肘を曲げて頭頂を手と手の間の地面につける', '肩で押す感覚', '腰、胸を反らせない']",
        'パイクプッシュアップ description+points'
    ))

    # ランジ
    edits.append((
        "description: '片足ずつ前に踏み込んで行う下半身のトレーニングです。タンブリングの片足踏み切りでとても大切です。',\n    points: ['前足の膝が90度になるまで下げる', '上体をまっすぐ保つ', '前足で押し戻す', '左右バランスよく']",
        "description: '片足ずつ前に踏み込んで行う、前方のタンブリングに必要不可欠な姿勢です。',\n    points: ['前足の膝が90度になるまで下げる', '上半身と後ろの足が一本の線になるように保つ', '後ろ足のかかとを浮かして、目線は前', 'お腹周りに力を入れる']",
        'ランジ description+points'
    ))

    # 垂直ジャンプ
    edits.append((
        "description: '膝を曲げてから真上に高く跳ぶ、いちばん基本のジャンプです。バク転や宙返りで「上に高く跳ぶ力」を作ります。',\n    points: ['膝を曲げて勢いをためる', '腕の振り上げを使って跳ぶ', '空中で体を伸ばす', '着地で衝撃を吸収']",
        "description: '膝を中腰の姿勢まで曲げてから真上に高く跳ぶ、いちばん基本のジャンプです。バク転や宙返りで「上に高く跳ぶ力」を作ります。',\n    points: ['膝を曲げて勢いをためる', '腕の振るタイミングと足で跳ぶタイミングを合わせる', '空中で身体を伸ばす', '着地で衝撃を吸収']",
        '垂直ジャンプ description+points'
    ))

    # アプローチジャンプ → アプローチジャンプ（Tモーションジャンプ）
    edits.append((
        "id: 'approach-jump', name: 'アプローチジャンプ', nameEn: 'Approach Jump'",
        "id: 'approach-jump', name: 'アプローチジャンプ（Tモーションジャンプ）', nameEn: 'T-Motion Jump'",
        'アプローチジャンプ 改名'
    ))
    edits.append((
        "description: '一歩踏み込み→両足踏み切り→ジャンプの流れを練習するジャンプです。ハンドスプリングやロンダートで必要な「ホップ → 両足踏み切り」のリズムを身につけます。',\n    points: ['一歩で大きく踏み込む', '両足を素早く揃える', '踏み切りで床をしっかり押す', '空中で体を一本に保つ']",
        "description: '両手を真横にキープして垂直ジャンプ、空中でTの形を作ります。トレーニングとして下半身の強化が期待できます。',\n    points: ['中腰のポジションまで膝を曲げてジャンプ', '腕の位置を変えず、つま先も意識して跳ぶ', '空中で身体を一本に保つ']",
        'アプローチジャンプ description+points'
    ))

    # 抱え込みジャンプ
    edits.append((
        "description: '空中で膝を胸にグッと引きつけるジャンプです。バク宙のときの抱え込み感覚を作ります。',\n    points: ['真上に高く跳ぶ', '空中で素早く膝を胸に', '着地は両足同時に', '上半身を反らさない']",
        "description: '空中で膝を胸の前まで持ち上げるジャンプです。宙返りの時の抱え込み感覚を作ります。',\n    points: ['真上に高く跳ぶ', '空中で素早く膝を胸に', '床をける瞬間に身体は垂直に保ち、つま先を使ってける', '上半身を反らさない、頭を下げない']",
        '抱え込みジャンプ description+points'
    ))

    # ストレートジャンプ
    edits.append((
        "description: '体をまっすぐ一本の棒のように保ったまま、真上に跳ぶジャンプです。レイアウトやフルの基礎になります。',\n    points: ['体を一本の棒に', 'お腹と腿を締める', '腕は上に伸ばす', 'できるだけ高く跳ぶ']",
        "description: '身体をまっすぐ一本の棒のように保ったまま、真上に跳ぶジャンプです。背骨に体重を感じてけり、レイアウトやフルの基礎になります。',\n    points: ['体を一本の棒に', '膝を曲げず、つま先だけを使って蹴る感覚取得', '腕は上に伸ばす', '膝を曲げず、足首、つま先を強化する']",
        'ストレートジャンプ description+points'
    ))

    # スタージャンプ
    edits.append((
        "description: '空中で手足を大きく星形に広げるジャンプです。やわらかさと跳ぶ力、空中での体の意識を同時に鍛えられます。',\n    points: ['真上に高く跳ぶ', '空中で手足を星形に開く', '腕は斜め上にしっかり伸ばす', '着地は両足同時']",
        "description: '空中で手足を大きく「星形」に身体を広げるジャンプです。上半身と下半身を同時に開き、全身のコントロールを鍛えられます。',\n    points: ['真上に高く跳ぶ', '空中で手足を星形に開く', '腕は真横に伸ばす', '頭は常に高い位置を保つ']",
        'スタージャンプ description+points'
    ))

    # 開脚前屈（パンケーキ）
    edits.append((
        "description: '足を横に開いた姿勢から前に倒れる柔軟運動です。腰まわりがやわらかくなり、側転や側宙の振り上げ脚に効果があります。',\n    points: ['まっすぐ前に倒れる', '無理のない範囲で', '呼吸を止めない', '徐々に深くしていく']",
        "description: '足を横に開いた姿勢から前に倒れる柔軟運動です。股関節まわりの柔軟性、側転や側宙の振り上げ脚に効果があります。',\n    points: ['膝、つま先に力を入れて行う（膝の向きは前）', '床とお腹の間に隙間がないように前に倒れる', '呼吸を止めず、少しずつ下げる']",
        'パンケーキ description+points'
    ))

    # 前後開脚
    edits.append((
        "description: '前足を前に伸ばし、後ろ足をうしろに引いた形の開脚です。前方・後方ウォークオーバーやエアリアルで必要です。',\n    points: ['腰の正面が前を向く', '前後の足を一直線に', '左右両方練習', '毎日コツコツ']",
        "description: '前後に足を開き、床に脚が180度開く開脚の姿勢です。前方・後方ウォークオーバーやエアリアルに必要です。',\n    points: ['腰の正面が前を向く', '膝の向きは「前の足は上、後ろの足は下」になるように', '左右両方練習を続ける', '上半身が下がらないように垂直を保つ']",
        '前後開脚 description+points'
    ))

    # 横開脚
    edits.append((
        "description: '足を左右にまっすぐ180度開く開脚です。やわらかさのいちばんの目標で、側宙やキック技で効果があります。',\n    points: ['つま先を上に向ける', '腰を後ろに引かない', '呼吸を深く', 'お風呂上がりに練習']",
        "description: '足を左右にまっすぐ180度開く開脚です。股関節などの柔軟の代表例で、側宙やキック技に効果があります。',\n    points: ['膝、つま先に力を入れて行う（膝の向きは前）', '床とお腹の間に隙間がないように前に倒れる', '膝の向きを前に向ける']",
        '横開脚 description+points'
    ))

    # ブリッジ静止
    edits.append((
        "description: 'ブリッジの姿勢を長くキープする柔軟トレーニングです。背中・肩まわり・胸のやわらかさを作ります。',\n    points: ['腕をまっすぐ伸ばす', '肩を完全に開く', '胸を前に押し出す', '足は腰幅で']",
        "description: 'ブリッジの姿勢を正しくキープする柔軟です。背中・肩まわり・胸のやわらかさを作ります。',\n    points: ['腕をまっすぐ伸ばす', '肩を開き、手首の上に保つ', '両手、両足を歪まないように左右対称で揃える', '足は腰幅で保ち、つま先の向きは正面']",
        'ブリッジ静止 description+points'
    ))

    # 肩のストレッチ
    edits.append((
        "description: '肩を前後やぐるりと動かせる範囲を広げるストレッチです。倒立やバク転でとても大切です。',\n    points: ['前後・左右・回旋すべて', '無理に引っ張らない', '毎日継続', '体操選手の柔軟が参考に']",
        "description: 'ブリッジ系の技で必要な肩の動きの範囲を広げるストレッチです。倒立やバク転にもとても大切な柔軟です。',\n    points: ['猫が伸びをするようなイメージ', '肩や胸が床につくように', '腰を膝の上に保つ', '硬さを感じる選手は20-30回のバウンドもおすすめ']",
        '肩のストレッチ description+points'
    ))

    # 胸開きストレッチ → ハーフブリッジ
    edits.append((
        "id: 'chest-opener', name: '胸開きストレッチ', nameEn: 'Chest Opener'",
        "id: 'chest-opener', name: '胸開きストレッチ（ハーフブリッジ）', nameEn: 'Chest Stretch'",
        '胸開きストレッチ 改名'
    ))
    edits.append((
        "description: '胸の前を大きく開くストレッチです。ブリッジやバク転で反るために必要な、動かせる範囲を広げます。',\n    points: ['壁を使ってじんわり', '呼吸を深く', '反動を使わない', 'ぐっと開く感覚']",
        "description: '胸を大きく開くストレッチです。ブリッジやバク転などで正しく身体を開くために必要な姿勢です。',\n    points: ['足は肩幅に開く', '胸や背中の筋肉を使って開く', 'アゴは最大限に上げる', '肩はかかとの真上に保つ']",
        '胸開きストレッチ description+points'
    ))

    # 手首ストレッチ
    edits.append((
        "description: '手首を前後・左右に動かして可動域を広げるストレッチです。倒立・前転・ハンドスプリングなど、手で体重を支えるすべての技の前に必ず行います。',\n    points: ['手のひらを下に向けて手首を反らす', '手のひらを上に向けて手首を曲げる', '左右の側面にも倒す', '痛みを感じない範囲で']",
        "description: '手首の動かせる範囲を広げるストレッチです。倒立・前転・ハンドスプリングなど、手で体重を支えるすべての技の前に必ず行います。',\n    points: ['手のひらを下に向けて手首を反らす', '手のひらを上に向けて手首を曲げる', '肩が手首の後ろになるようにセット', '肘を伸ばして最大限に筋肉を伸ばす']",
        '手首ストレッチ description+points'
    ))

    # 首ストレッチ
    edits.append((
        "description: '首を前後・左右・回旋に動かしてほぐすストレッチです。前転・後転・倒立・ブリッジなど、首に負担がかかる技の前に必ず行います。',\n    points: ['ゆっくり大きく動かす', '反動を使わない', '痛みのない範囲で', 'ウォームアップに必ず実施']",
        "description: '床に寝転がり、腰を持ち上げて首をほぐすストレッチです。前転・後転・倒立・ブリッジなど、首に負担がかかる技の前に必ず行います。',\n    points: ['ゆっくり動かして準備をする', '足を肩幅に開いて、膝を顔の横に保つ', '痛みのない範囲で呼吸を忘れずに行う']",
        '首ストレッチ description+points'
    ))

    # ============================================================
    # スキル名の変更
    # ============================================================

    # ロンダート バク宙 → ロンダート〜抱え込み宙返り
    edits.append((
        "id: 'roundoff-tuck', name: 'ロンダート バク宙', nameEn: 'Round-off Back Tuck'",
        "id: 'roundoff-tuck', name: 'ロンダート〜抱え込み宙返り', nameEn: 'Round-off Back Tuck'",
        'ロンダート バク宙 改名'
    ))

    # ロンバク バク宙 → ロンバク〜宙返り
    edits.append((
        "id: 'rbht', name: 'ロンバク バク宙', nameEn: 'Round-off BHS Back Tuck'",
        "id: 'rbht', name: 'ロンバク〜宙返り', nameEn: 'Round-off BHS Back Tuck'",
        'ロンバク バク宙 改名'
    ))

    # レイアウト（伸身バク宙）→ レイアウト（伸身宙返り）
    # JSON にこの表記は無いかも。HTMLの skill name 'レイアウト' を 'レイアウト（伸身宙返り）' にする？
    # 既存：name: 'レイアウト'。Word doc: レイアウト（伸身バク宙）→ レイアウト（伸身宙返り） なので、HTMLは 'レイアウト' そのままだが、サブタイトルとしての扱い。
    # ただし HTML の name は 'レイアウト' (without サブタイトル)。 注釈用に nameEn を 'Layout' に保つ。

    # ============================================================
    # T() 呼び出し内の名前変更
    # ============================================================

    # 「ホロウホールド」を T() 引数として使ってる箇所を「腹筋ゆりかごキープ」に
    # ただし、index.html のtrainings 配列の name: 'ホロウホールド' は既に変えた
    # T('ホロウホールド', ...) は変える必要あり
    html_t_count_h = html.count("T('ホロウホールド'")
    html_t_count_a = html.count("T('アーチホールド'")
    html_t_count_h2 = html.count("T('ホロウホールド 強化'")  # 'ホロウホールド 強化' は別ラベルなので注意
    print(f'\n  T(ホロウホールド) 出現: {html_t_count_h}, T(アーチホールド): {html_t_count_a}, T(ホロウホールド 強化): {html_t_count_h2}')

    # ============================================================
    # まず通常のedits適用
    # ============================================================
    for old, new, desc in edits:
        if old not in html:
            print(f'  ⚠️  not found: {desc}')
            continue
        if html.count(old) > 1:
            print(f'  ⚠️  multiple matches({html.count(old)}件): {desc} — 最初の1件のみ置換')
        html = html.replace(old, new, 1)
        print(f'  ✓ {desc}')

    # ============================================================
    # T() 呼び出しの全置換（id 維持・表示名のみ変更）
    # ============================================================
    print('\n=== T() 呼び出しの一括更新 ===')
    html = patch_html_all(html, "T('ホロウホールド'", "T('腹筋ゆりかごキープ'", "T('ホロウホールド') → T('腹筋ゆりかごキープ')")
    html = patch_html_all(html, "T('ホロウホールド 強化'", "T('腹筋ゆりかごキープ 強化'", "T('ホロウホールド 強化') → T('腹筋ゆりかごキープ 強化')")
    html = patch_html_all(html, "T('アーチホールド'", "T('背筋キープ'", "T('アーチホールド') → T('背筋キープ')")

    # 説明文中の表記も整える（オプション、保守的に控えめ）
    # 例：「ホロウホールドや」「アーチホールド」が他の本文に出てくる場合は触らない（監督に判断委ねる）

    HTML_PATH.write_text(html, encoding='utf-8')
    print(f'\n✅ index.html 保存 ({len(html)} bytes)\n')


    # ============================================================
    # JSON の修正
    # ============================================================
    print('=== JSON を修正 ===')
    d = json.loads(JSON_PATH.read_text(encoding='utf-8'))

    def get_skill(sid):
        s = next((x for x in d['skills'] if x['id'] == sid), None)
        if not s:
            print(f'  ⚠️  not found: {sid}')
        return s

    def find_idx(items, title):
        for i, it in enumerate(items):
            if it['title'] == title:
                return i
        return -1

    def replace_item(items, old_title, new_title, new_detail=None):
        i = find_idx(items, old_title)
        if i < 0:
            print(f'    ⚠️  title not found: {old_title}')
            return False
        items[i]['title'] = new_title
        if new_detail is not None:
            items[i]['detail'] = new_detail
        return True

    def replace_detail(items, title, new_detail):
        i = find_idx(items, title)
        if i < 0:
            print(f'    ⚠️  title not found: {title}')
            return False
        items[i]['detail'] = new_detail
        return True

    def delete_item(items, title):
        i = find_idx(items, title)
        if i < 0:
            print(f'    ⚠️  title not found: {title}')
            return False
        items.pop(i)
        return True

    # ===== スタンド宙返り (standing_back_tuck) =====
    print('\n[スタンド宙返り]')
    s = get_skill('standing_back_tuck')
    if s:
        # points
        replace_item(s['points'], '踏み切った瞬間に膝を胸に引きつける', '踏み切った瞬間に腰（骨盤）を前に出す', '回転のきっかけを作る')
        replace_item(s['points'], '腰を反らせず真上に飛んでから回す', '跳んだ時に身体を一瞬伸ばして抱え込む', '垂直ではく、跳んだ時に多少身体に角度をつける')
        replace_item(s['points'], '回転半分で開きを意識し両足同時着地', '着地の直前に両手を足から離し着地の準備', '衝撃吸収')
        # cautions
        if s.get('cautions'):
            replace_detail(s['cautions'], 'バク転を完璧にしてから', 'バク転の経験があった方が後方に跳ぶ恐怖心が軽減される')
        # common_mistakes
        replace_item(s['common_mistakes'], '後ろに飛び過ぎる', '後ろに飛び過ぎて高さが出ない', '肩を後ろに倒し過ぎて、蹴った時のパワーが半減する')

    # ===== ロンダート バク宙 (round_off_back_tuck) =====
    print('\n[ロンダート バク宙 → ロンダート〜抱え込み宙返り]')
    s = get_skill('round_off_back_tuck')
    if s:
        s['name'] = 'ロンダート〜抱え込み宙返り'
        # points
        replace_item(s['points'], '抱え込みは早く解くのも早く', 'リバウンドの瞬間に身体を伸ばす', 'ばんざいの姿勢を作る')
        replace_item(s['points'], '体軸を崩さず垂直軸で回す', 'ばんざいの姿勢から腕を垂直より前に腕を動かさない', '回転を止める動作になるため')
        replace_item(s['points'], '着地は両足同時', '着地は両足同時', 'つま先から着地をして衝撃を吸収')
        # cautions
        if s.get('cautions'):
            replace_item(s['cautions'], 'ロンバクとスタンド宙返りを完璧に', 'ロンダート、スタンド宙返りの完成度を高く維持', '前提必須')
            replace_item(s['cautions'], '高マットで感覚を作ってから床へ', 'タンブリング板やエアーマットなどで感覚を作ってから床へ', '段階厳守')
        # common_mistakes
        replace_detail(s['common_mistakes'], '進む勢いを宙返りに変換できない', '床をける時に身体が垂直ではなく、傾きすぎている')
        replace_detail(s['common_mistakes'], '飛ぶ前に上を見る', '自分の位置が分からなくなる')
        replace_detail(s['common_mistakes'], '着地で前に流れる', '宙返りのける角度が悪く、膝が抜ける')
        # progression
        replace_item(s['progression'], '高マットでのバク宙', 'タンブリング板やエアーマットなどで使用', '正しい位置を覚える')

    # ===== ロンバク バク宙 (round_off_bhs_back_tuck) → ロンバク〜宙返り =====
    print('\n[ロンバク バク宙 → ロンバク〜宙返り]')
    s = get_skill('round_off_bhs_back_tuck')
    if s:
        s['name'] = 'ロンバク〜宙返り'
        s['description'] = 'ロンダート〜バク転〜宙返りをひと続きで繋ぐ3連続技で、チア・体操の代表的な組み合わせです。バク転を独立した技として扱うのではなく「宙返りの高さを生み出す加速の動作」としてイメージです。'
        # points
        replace_item(s['points'], 'バク転の手着き→押しで真上へ', 'バク転の手着き〜コルベットを意識', '身体をひっくり返る動作を覚えて垂直方向へ変換')
        replace_item(s['points'], '3つの技を「1つの流れ」に', '3つの技を「一連の動作」に', '体に正しい動きを覚えさせる')
        delete_item(s['points'], '各局面でリズムを途切れさせない')
        # cautions
        if s.get('cautions'):
            replace_item(s['cautions'], 'ロンバクとロン宙を完璧に', 'ロンバクを完璧に', '前提必須')
            replace_item(s['cautions'], 'リズムを力で押し切らない', 'リズムだけで行わない', '一つ一つの技術が重要')
        # common_mistakes
        replace_item(s['common_mistakes'], 'バク転で勢いを殺す', 'バク転で勢いを止めてしまう', '加速の役割を果たせない')
        replace_item(s['common_mistakes'], 'バク宙で頭が下がる', '宙返りで頭が下がる', '回転軸が下に倒れる')
        replace_item(s['common_mistakes'], 'リズムが乱れる', 'リズムが乱れる', '一つ一つの技術が不安定')
        # progression
        replace_item(s['progression'], 'ロンダート→バク転→ジャンプ', 'ロンダート〜バク転〜ジャンプ', 'コンビネーションの感覚作り')
        replace_item(s['progression'], '補助付きで完全な3連', '補助付きで完全なコンビネーション', 'コーチが支える')

    # ===== パンチフロント (punch_front) =====
    print('\n[パンチフロント]')
    s = get_skill('punch_front')
    if s:
        s['description'] = '助走で前進する速さを、両足同時の踏み切り(パンチ)で真上方向に変えて、抱え込んで前方に一回転する技です。両足同時の踏み切りが片足になると力が分散して回り切れないため、最後の踏切のタイミングが最重要ポイントです。'
        # points
        replace_item(s['points'], '腕を上に振り上げ上半身を巻き込む', '床をけった瞬間に腰を後ろに持ち上げる', '回転開始')
        replace_item(s['points'], '抱え込みは素早く回転を作る', '腰を後ろに持ち上げると同時には素早く抱え込む', '小さくして速く回る')
        replace_item(s['points'], '着地は前進方向に勢いを止めない', '着地は垂直に足を下ろすように重心を落とす', '着地の安定性につながる')
        # cautions
        if s.get('cautions'):
            replace_item(s['cautions'], '前方ハンドスプリングと前方エアリアルが前提', '高速の前転が前提', '基本必須')
            replace_item(s['cautions'], '片足踏み切りにならないよう確認', '片足踏み切りにならないよう確認', '最後の踏切')
        # common_mistakes
        replace_item(s['common_mistakes'], '回転不足で背中・お尻から落ちる', '回転不足で背中・お尻から落ちる', '背骨などに負担がかかる')
        replace_item(s['common_mistakes'], '助走を活かせない', '助走を活かせない', 'ける瞬間に膝が抜けて失速する')
        # progression
        replace_item(s['progression'], '高マットからのパンチフロント', 'タンブリング板やエアーマットなどでパンチフロント', 'ける力を補助')
        delete_item(s['progression'], 'ハンドスプリングからのパンチフロント')

    # ===== レイアウト (layout) → レイアウト（伸身宙返り） =====
    print('\n[レイアウト（伸身バク宙）→ レイアウト（伸身宙返り）]')
    s = get_skill('layout')
    if s:
        s['name'] = 'レイアウト（伸身宙返り）'
        s['description'] = '身体を一本の棒のように保ったまま、後方に一回転する宙返りです。身体が長い分だけ回るのに時間がかかるため、ロンバクで作った高さ、回転をかける骨盤を前に出す動作が成功の絶対条件となります。フル、ダブルフルなどひねり技すべての土台です。'
        # points
        replace_item(s['points'], 'バク転からとにかく高く飛ぶ', 'バク転から高くストレートジャンプ', '高さが絶対条件')
        replace_item(s['points'], '体を伸ばしたまま肩で回す', '骨盤を前、手の指先を後ろに方向を変える', '身体を伸ばしたまま回転を生み出す')
        # cautions
        if s.get('cautions'):
            replace_item(s['cautions'], '必ず補助者をつけて練習', 'トランポリンで練習', '回転のきっかけを理解しやすい')
        # common_mistakes
        replace_item(s['common_mistakes'], '抱え込みグセが残る', '回転をかける骨盤を前に出す動作が足りない', '途中で曲がってしまう')
        replace_item(s['common_mistakes'], '高さ不足で回り切れない', '高さ不足になる', '正しい角度で、フルパワーで床を蹴れていない')
        # progression
        replace_item(s['progression'], 'バク宙で高さを最大化', '宙返りで高さを最大化', '回転時間を確保する')
        replace_detail(s['progression'], '伸身意識のバク宙練習', '体を伸ばす感覚作りを細分化したドリルを行う')
        replace_item(s['progression'], '連続で完成度を上げる', '継続的に完成度の高いレイアウトができる', '安定して実施できる')

    # ===== フル (full_twist) =====
    print('\n[フル（バク転→1回ひねり）]')
    s = get_skill('full_twist')
    if s:
        s['description'] = 'レイアウトを土台に、空中で横軸の1回ひねりを加える技です。宙返りという前後の回転の最中に、コマのような横回転を重ねる「2軸の同時回転」で、ひねりは身体の中心を軸に身体の左右非対称の動きをつくり、ひねりを発生させます。'
        # points
        replace_item(s['points'], 'ひねりは肩から開始', 'ひねりは片方の肩から開始', '左右非対称の動きをつくり、ひねりを発生させる')
        replace_item(s['points'], '着地までひねりを完了', '着地までひねりを完了', '正面までひねりきる')
        # common_mistakes
        replace_item(s['common_mistakes'], '回転と同時にひねろうとする', 'ひねりを先にしようとする', '縦回転が足りず、回転不足になる')
        replace_item(s['common_mistakes'], '高さ不足でひねり切れない', 'ひねり不足でひねり切れない', '身体が反ったレイアウトをして、ひねりをかけるタイミングが遅れる')
        delete_item(s['common_mistakes'], '着地が斜めになり止まれない')
        replace_item(s['common_mistakes'], '腕の引き込みが弱い', 'バク転後の腕の位置が低い', 'ばんざいの姿勢からひねりをかけないと縦回転、横回転両方が発生しない')
        # progression
        replace_detail(s['progression'], 'トランポリンでフルひねり', '空中で正しい身体の姿勢、動作習得')
        replace_item(s['progression'], '高マットでのフル', 'タンブリング板やエアーマット、エバーーマットなどでロンバク〜フル', '高さを利用、また柔らかいマットを使用して安全に実施')

    # ===== ウィップバック (whip_back) =====
    print('\n[ウィップバック]')
    s = get_skill('whip_back')
    if s:
        s['description'] = '手を着かずに行う後ろ向きの伸身回転で、連続技を繋ぐ技です。単独で行う技ではなく、必ず次のバク宙やひねり技と組み合わせて使い、後方にスピードを途切れさせないことが目的になります。'
        # points
        replace_item(s['points'], 'バク転と同じ動きで手を着かない', '低いレイアウトをイメージ', 'バク転で手をつかないイメージだけでは後半の動きが追いつかない')
        replace_item(s['points'], '体を伸ばしたまま肩で回転', '身体を伸ばしたまま腕を斜め４５°後ろに腕を振る', '伸身姿勢を保つ')
        delete_item(s['points'], '「加速器」として使う')
        replace_item(s['points'], '必ず次の技とセットで練習', '後ろに進み続ける勢いをなくさない', '身体が後ろに進んでいる状態を保つ')
        # cautions
        if s.get('cautions'):
            replace_item(s['cautions'], '必ず補助者をつけて練習', 'トランポリン、タンブリング板、エアーマットなどで練習', '正しい角度を覚える')
        # common_mistakes
        replace_item(s['common_mistakes'], '無意識に手を着く', '伸びが足りず高さが出てしまう', '後ろに引っ張らず、上に引き上げてしまう')
        replace_item(s['common_mistakes'], '次の技に繋がらない', 'ける時に膝が曲がる', '失速する')
        # progression
        replace_detail(s['progression'], 'ロンダート〜高くバク転', '高さの正しいエバーマットやBoxを使い、跳ぶ方向')
        replace_item(s['progression'], '補助付きでウィップ', 'ロンダート〜バクバクをつなげる', '限りなく近いリズムの技をつなげる')
        replace_item(s['progression'], 'ロンダート〜ウィップ〜バク転', 'タントラ（長いトランポリン）でウィップの連続', '接続の確認')
        replace_item(s['progression'], '自力で連続技に組み込む', 'ロンダート〜後ろにジャンプで後方に勢いをつなげる', '自力で行う')

    # ===== ダブルフル (double_full) =====
    print('\n[ダブルフル]')
    s = get_skill('double_full')
    if s:
        s['description'] = 'レイアウト1回宙返りの間に、身体の中心軸を基準に横軸の2回ひねりを完成させる最高難度レベルの技です。フルよりさらに高い踏み切りと身体の中心を軸に、身体の左右非対称の動きをつくり、ひねりを発生させます。チアでも一握りの選手にしかできません。'
        # points
        replace_item(s['points'], 'フルよりさらに高く飛ぶ', '空中でフルを早く完成させる', 'さらにひねるための余裕が必要')
        replace_item(s['points'], 'ひねりの加速を一気にかける', '回転をかけすぎないように上に上がるレイアウトを行う', '縦回転はける瞬間のみ意識をする')
        replace_item(s['points'], '回転を2回完了させてから着地', '回転を2回完了させてから着地', '中途半端で開かないように身体を力を入れ続ける')
        # common_mistakes
        delete_item(s['common_mistakes'], 'ひねりが1.5回で止まる')
        replace_item(s['common_mistakes'], '軸がずれて斜めに着地', '正しいレイアウトができず反ってしまう', '回転がかかりすぎて高さが出ない')
        replace_item(s['common_mistakes'], '高さ不足で失敗', '高さ不足で失速', 'ける瞬間に全身に力が入っていない')
        replace_item(s['common_mistakes'], 'ひねりの開始が遅い', 'ひねりがかからない', '身体が真っ直ぐでないため、ひねりひねりのスタートができない')

    # ===== アラビアン (arabian) =====
    print('\n[アラビアン]')
    s = get_skill('arabian')
    if s:
        s['description'] = '後方に踏み切った直後に1/2ひねりを完了させ、そのまま前方の抱え込み宙返りに切り替えるトリッキーな技です。一般的にロンダートから入り、後方への勢いを半ひねりで前回転に切り替える、ひねりと前まわりの接続タイミングが鍵となります。'
        # points
        replace_item(s['points'], 'ロンバクからバク宙の入り', 'ロンダートから宙返りの入り', '縦回転をなくさない')
        replace_item(s['points'], '前方着地で前進を止める', '前方着地で前進を止める', '膝を曲げて着地を吸収')
        # cautions
        if s.get('cautions'):
            replace_item(s['cautions'], 'フルと前宙を完璧にしてから', '宙返り1/2ひねりと前宙を完璧にしてから', '前提条件が複合')
        # common_mistakes
        replace_item(s['common_mistakes'], '前方宙への切り替えが遅れる', '前方宙への切り替えが遅れる', '宙返り1/2ひねりになる')
        delete_item(s['common_mistakes'], '着地で前に流れすぎる')
        replace_item(s['common_mistakes'], 'ひねりが浅い', 'ひねりが早すぎる', '回転がかからず斜めに曲がる')

    # JSON 保存
    JSON_PATH.write_text(json.dumps(d, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(f'\n✅ JSON 保存 ({len(d["skills"])}技)')


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
