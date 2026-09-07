# -*- coding: utf-8 -*-
"""
index.html の技データから「技画面の改善」用の下書きを 33 技分まとめて生成する。

技を2種類に分ける（2026-09-07 監督指示）:

  ■ 基礎技（Lv0 以下）… 8技
      直す方法は不要。土台になる技なので「ポイント3つ」＋「注意1〜2つ」だけ。
      → points / mistakes からそのまま作れるので、監督の記入はほぼ不要。

  ■ 技（Lv1 以上）… 25技
      「起きている現象（症状）」→「直し方（一言）」だけ。
      原因を型で分けるのは選択肢が増えて複雑になるため採用しない。

※ 指導内容は新規に作らない。すべて index.html の既存データが元。
"""
import re, json, io

SRC = 'index.html'
OUT = 'data/skill_errors_draft.json'
BASIC_MAX_LEVEL = 0.0     # これ以下は「基礎技」扱い

s = io.open(SRC, encoding='utf-8').read()
block = s[s.index('const skills = ['): s.index('const skillsByPrereq')]

# ---- 技ごとに切り出す ----
starts = [m.start() for m in re.finditer(r"\n  \{\n?\s*id: '", block)]
starts.append(len(block))
skills, order = {}, []
for a, b in zip(starts, starts[1:]):
    seg = block[a:b]
    m = re.search(r"id: '([^']+)'", seg)
    if not m:
        continue
    sid = m.group(1)
    name = (re.search(r"name: '([^']+)'", seg) or [None, sid])[1]
    lvm = re.search(r"level: (-?[\d.]+)", seg)
    level = float(lvm.group(1)) if lvm else 99.0

    def lst(key):
        # 最初の ] で必ず閉じる。次の配列や prereqTypes を巻き込まない。
        mm = re.search(key + r": \[([^\]]*)\]", seg, re.S)
        return re.findall(r"'([^']+)'", mm.group(1)) if mm else []

    trains = []
    mt = re.search(r"trainings: \[(.*?)\n    \]", seg, re.S)
    if mt:
        for t in re.findall(r"T\(\s*'([^']+)'\s*,\s*(?:'([^']*)'|null)", mt.group(1)):
            trains.append({'name': t[0], 'target': t[1] or ''})

    skills[sid] = {
        'id': sid, 'name': name, 'level': level,
        'mistakes': lst('mistakes'),
        'points': lst('points'),
        'progression': lst('progression'),
        'prereqs': [x for x in lst('prereqs') if re.fullmatch(r'[a-z0-9-]+', x)],
        'trainings': trains,
    }
    order.append(sid)

# ---- 監督が過去に書いた症状リスト ----
sym = {}
seg = s[s.index('const SKILL_SYMPTOMS = {'):]
seg = seg[:seg.index('\n};')]
for sid, body in re.findall(r"'([\w-]+)': \[(.*?)\]", seg, re.S):
    sym[sid] = [t for t, _ in re.findall(r"title: '([^']+)', premium: (\w+)", body)]

out = []
for sid in order:
    sk = skills[sid]
    is_basic = sk['level'] <= BASIC_MAX_LEVEL

    rec = {
        'id': sid,
        'name': sk['name'],
        'level': sk['level'],
        'kind': 'basic' if is_basic else 'skill',
        'confirmed': False,
        'ref_mistakes': sk['mistakes'],
        'ref_points': sk['points'],
    }

    if is_basic:
        # 基礎技：ポイント3つ＋注意1〜2つ。既存データから下書きが完成する。
        rec['points'] = sk['points'][:3]
        rec['cautions'] = sk['mistakes'][:2]
    else:
        # 技：症状 → 直し方（一言）。直し方は監督が記入。
        titles = sym.get(sid) or sk['mistakes']
        rec['errors'] = [{'title': t, 'fix': ''} for t in titles]
        rec['from_symptoms'] = sid in sym
        rec['trainings'] = sk['trainings']
        rec['progression'] = sk['progression']
        rec['prereqs'] = [{'id': p, 'name': skills.get(p, {}).get('name', p)} for p in sk['prereqs']]

    out.append(rec)

io.open(OUT, 'w', encoding='utf-8').write(json.dumps(out, ensure_ascii=False, indent=2))

basics = [x for x in out if x['kind'] == 'basic']
tricks = [x for x in out if x['kind'] == 'skill']
errs = [e for x in tricks for e in x['errors']]
short = [e for e in errs if len(e['title']) <= 12]
print(f"技: {len(out)}")
print(f"■ 基礎技（Lv{BASIC_MAX_LEVEL:.0f}以下）: {len(basics)}技")
print(f"    ポイント3つが揃った : {sum(1 for x in basics if len(x['points']) == 3)}技")
print(f"    注意が1つ以上ある   : {sum(1 for x in basics if x['cautions'])}技")
print(f"■ 技（Lv1以上）      : {len(tricks)}技　症状 {len(errs)}件")
print(f"    症状名がそのまま使える（12字以内）: {len(short)}件 / 要短縮 {len(errs)-len(short)}件")
print(f"    直し方の記入が必要  : {len(errs)}件")
print(f"出力: {OUT}")
