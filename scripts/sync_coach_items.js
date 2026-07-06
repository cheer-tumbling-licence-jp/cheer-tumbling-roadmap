#!/usr/bin/env node
// coach_items.json を index.html の skills / trainings 配列から自動生成する。
//
// これまで手作業で coach_items.json を維持していたため、動画パイプラインで
// index.html に新規 training が追加されても coach 側 (課題を出す画面) に反映
// されず、監督から「トレーニング項目が少ない」と指摘された（2026-07-04）。
//
// index.html の `const trainings = [ ... ];` と `const skills = [ ... ];`
// を切り出して評価し、coach_items.json に必要なフィールドだけ投影する。

const fs = require('fs');
const path = require('path');
const vm = require('vm');

const ROOT = path.resolve(__dirname, '..');
const INDEX_HTML = path.join(ROOT, 'index.html');
const OUT = path.join(ROOT, 'data', 'coach_items.json');

function extractArray(source, varName) {
  const marker = `const ${varName} = [`;
  const start = source.indexOf(marker);
  if (start < 0) throw new Error(`${varName} not found`);
  // 対応する ]; を探す（ブラケット深度で厳密に）
  let depth = 0;
  let i = start + `const ${varName} = `.length;
  const arrStart = i;
  for (; i < source.length; i++) {
    const ch = source[i];
    if (ch === '[') depth++;
    else if (ch === ']') {
      depth--;
      if (depth === 0) {
        return source.slice(arrStart, i + 1);
      }
    }
  }
  throw new Error(`${varName}: closing bracket not found`);
}

const html = fs.readFileSync(INDEX_HTML, 'utf8');
const trainingsSrc = extractArray(html, 'trainings');
const skillsSrc = extractArray(html, 'skills');

// skills 配列は T(name, target, query, trainingId) ヘルパー（index.html 4043 行付近で定義）
// を参照するため、eval 用に同じ形の T を渡す
const ctx = { T: (name, target, query, trainingId) => ({ name, target, query: query || name, trainingId }) };
vm.createContext(ctx);
const trainings = vm.runInContext(trainingsSrc, ctx);
const skills = vm.runInContext(skillsSrc, ctx);

// coach_items.json 形式に投影
const items = [];
for (const s of skills) {
  items.push({
    type: 'skill',
    id: s.id,
    name: s.name,
    level: typeof s.level === 'number' ? s.level : -1,
    category: s.category || '',
    description: s.description || '',
    tags: s.tags || [],
  });
}
for (const t of trainings) {
  items.push({
    type: 'training',
    id: t.id,
    name: t.name,
    category: t.category || '',
    description: t.description || '',
    keywords: [
      ...(t.points || []),
      ...(t.tags || []),
      t.nameEn || '',
    ].filter(Boolean),
  });
}

// 既存 coach_items.json のトップレベルキーは items のみだが、将来拡張のため merge
let existing = {};
try { existing = JSON.parse(fs.readFileSync(OUT, 'utf8')); } catch (_) {}
const output = { ...existing, items };

fs.writeFileSync(OUT, JSON.stringify(output, null, 2) + '\n', 'utf8');
console.log(`✅ ${OUT} を更新: skills=${skills.length}, trainings=${trainings.length}`);
