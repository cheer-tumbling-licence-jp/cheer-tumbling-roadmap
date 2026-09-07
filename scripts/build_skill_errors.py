# -*- coding: utf-8 -*-
"""
index.html の技データ（mistakes / points / progression / trainings / prereqs）から
「エラー診断」用の下書きデータを 33 技分まとめて生成する。

- エラー名  ← SKILL_SYMPTOMS があればそれ、無ければ mistakes から生成
- なぜ起きるか ← mistakes の文（監督の言葉）を短縮
- 見るところ  ← points の中から関連の強いものを選ぶ（監督の言葉）
- トレーニング ← trainings（そのまま）
- 段階練習   ← progression（そのまま）
- 前の技    ← prereqs（そのまま。恐怖・土台系のエラーのみ付与）

※ 文章はすべて監督の既存データが元。新しい指導内容は作らない。
"""
import re, json, io, sys

SRC = 'index.html'
OUT = 'data/skill_errors_draft.json'

s = io.open(SRC, encoding='utf-8').read()
block = s[s.index('const skills = ['): s.index('const skillsByPrereq')]

# ---- 技ごとに切り出す ----
starts = [m.start() for m in re.finditer(r"\n  \{\n?\s*id: '", block)]
starts.append(len(block))
skills = {}
order = []
for a, b in zip(starts, starts[1:]):
    seg = block[a:b]
    m = re.search(r"id: '([^']+)', name: '([^']+)', nameEn: '([^']*)', level: ([\d.]+)", seg)
    if not m:
        m2 = re.search(r"id: '([^']+)', name: '([^']+)'", seg)
        if not m2: continue
        sid, name, en, lv = m2.group(1), m2.group(2), '', ''
    else:
        sid, name, en, lv = m.groups()

    def lst(key):
        # 最初の ] で必ず閉じる。次の配列や prereqTypes を巻き込まない。
        mm = re.search(key + r": \[([^\]]*)\]", seg, re.S)
        return re.findall(r"'([^']+)'", mm.group(1)) if mm else []

    # trainings は T('名前','回数',...) 形式なので名前と回数だけ取る
    trains = []
    mt = re.search(r"trainings: \[(.*?)\n    \]", seg, re.S)
    if mt:
        for t in re.findall(r"T\(\s*'([^']+)'\s*,\s*(?:'([^']*)'|null)", mt.group(1)):
            trains.append({'name': t[0], 'target': t[1] or ''})

    skills[sid] = {
        'id': sid, 'name': name, 'nameEn': en, 'level': lv,
        'mistakes': lst('mistakes'),
        'points': lst('points'),
        'progression': lst('progression'),
        'prereqs': [x for x in lst('prereqs') if re.fullmatch(r'[a-z0-9-]+', x)],
        'trainings': trains,
    }
    order.append(sid)

# ---- 既存の症状リスト（監督が過去に書いたもの）----
sym = {}
seg = s[s.index('const SKILL_SYMPTOMS = {'):]
seg = seg[:seg.index('\n};')]
for sid, body in re.findall(r"'([\w-]+)': \[(.*?)\]", seg, re.S):
    sym[sid] = [{'title': t, 'premium': p == 'true'}
                for t, p in re.findall(r"title: '([^']+)', premium: (\w+)", body)]

# ---- 「見るところ」を points から選ぶ（語の重なりで判定）----
def grams(t):
    t = re.sub(r'[^ぁ-んァ-ヶ一-龥ー]', '', t)
    return {t[i:i+2] for i in range(len(t) - 1)}

def best_match(text, cands, used, min_score):
    """重なりが min_score 未満なら None を返す（推測で埋めない）"""
    best, score = None, 0
    g = grams(text)
    for c in cands:
        if c in used: continue
        sc = len(g & grams(c))
        if sc > score:
            best, score = c, sc
    return best if score >= min_score else None

# 前の技へ誘導すべきエラーのキーワード
BACK_WORDS = ['怖', 'こわ', '不安', '回りきれ', '固ま', '硬', '入れない']

out = []
for sid in order:
    sk = skills[sid]
    errs = []
    titles = [x['title'] for x in sym.get(sid, [])]
    sources = titles if titles else sk['mistakes']
    used_points, used_mistakes = set(), set()
    for title in sources:
        # なぜ起きるか：症状リスト由来のときだけ mistakes と突き合わせる
        # 症状と mistakes は別々に書かれており機械的な対応は誤りやすい。
        # 推測で埋めず空欄にし、レビュー画面に元データを参考表示する。
        why = None
        pt = best_match(title + (why or ''), sk['points'], used_points, 2)
        if pt: used_points.add(pt)
        needs_back = bool(any(w in title for w in BACK_WORDS) and sk['prereqs'])
        errs.append({
            'title': title,
            'why': [why] if why else [],
            'watch': [pt] if pt else [],
            'needs_back': needs_back,
            'confirmed': False,
        })
    out.append({
        'id': sid, 'name': sk['name'], 'level': sk['level'],
        'from_symptoms': bool(titles),
        'errors': errs,
        'trainings': sk['trainings'],
        'progression': sk['progression'],
        'ref_mistakes': sk['mistakes'],
        'ref_points': sk['points'],
        'prereqs': [{'id': p, 'name': skills.get(p, {}).get('name', p)} for p in sk['prereqs']],
    })

io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=2))

errs_all = [e for x in out for e in x['errors']]
need_why   = [e for e in errs_all if not e['why']]
need_watch = [e for e in errs_all if not e['watch']]
print(f"技: {len(out)}　エラー下書き: {len(errs_all)} 件")
print(f"  監督の症状リストが元 : {sum(1 for x in out if x['from_symptoms'])} 技")
print(f"  「なぜ」が埋まった   : {len(errs_all)-len(need_why)} 件 / 空欄 {len(need_why)} 件")
print(f"  「見るところ」が埋まった: {len(errs_all)-len(need_watch)} 件 / 空欄 {len(need_watch)} 件")
bad = [p['id'] for x in out for p in x['prereqs'] if p['id'] == p['name']]
print(f"  前の技の名前が引けなかったID: {sorted(set(bad)) or 'なし'}")
print(f"出力: {OUT}")
