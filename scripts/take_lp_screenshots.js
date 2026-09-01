#!/usr/bin/env node
/*
 * 販促物用アプリスクリーンショット撮影
 * 前提：preview server (http://localhost:5191) が起動していること
 *
 * 出力：assets/lp-screenshots/{mobile,desktop}/*.png
 *   - mobile/01_home.png             ホーム（サンプル選手:さき選択中）
 *   - mobile/02_skills_accordion.png 技一覧アコーディオン
 *   - mobile/03_skill_detail.png     技詳細（バク転・動画＋USAレベル）
 *   - mobile/04_practice_menu.png    練習メニュー
 *   - mobile/05_progress_heatmap.png 成長記録ヒートマップ ★サンプル選手データで色付き
 *   - mobile/06_program_circuit.png  練習プログラム＋指導配置図 ★生成後
 *   - mobile/07_streak.png           ストリーク表示（メニュー or 進捗から）
 *   - desktop/01_program_circuit.png コーチ向け：サーキット配置図（広い画面）
 *   - desktop/02_progress_heatmap.png コーチ向け：選手全員のヒートマップ
 */
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

const BASE = 'http://localhost:5191/index.html?demo=1&sample=1';
const OUT = path.join(__dirname, '..', 'assets', 'lp-screenshots');
fs.mkdirSync(path.join(OUT, 'mobile'), { recursive: true });
fs.mkdirSync(path.join(OUT, 'desktop'), { recursive: true });

const sleep = ms => new Promise(r => setTimeout(r, ms));

async function clickByText(page, regex) {
  const handle = await page.evaluateHandle((src) => {
    const re = new RegExp(src);
    // div ベースのタイル・タブ・カード・onclick 要素も含めて広く探す
    // このアプリの主要ナビは .tab.tab-main / .tab.tab-sub（div）と .quick-title
    const sel = 'button, a, [role="tab"], [role="button"], [onclick], .tab, .quick-title, .feature-title, [class*="tile"], [class*="card"], [class*="btn"], [data-tab], [class*="nav"] > *';
    const els = [...document.querySelectorAll(sel)];
    // マッチするなかで「クリックできる最深要素」を返す（親も子もマッチしたら子を優先）
    const matches = els.filter(e => re.test(e.textContent || ''));
    if (matches.length === 0) return null;
    // 最も小さい（テキスト量が少ない = 具体的な要素）を返す
    matches.sort((a, b) => (a.textContent || '').length - (b.textContent || '').length);
    return matches[0];
  }, regex.source);
  const el = handle.asElement();
  if (!el) throw new Error(`element not found: ${regex}`);
  await el.click();
  await sleep(700);
}

async function tryClickByText(page, regex) {
  try { await clickByText(page, regex); return true; }
  catch(e) { console.log('  ! skip:', regex.source); return false; }
}

// data-tab 属性でタブを直接切替（skills / trainings / menu / progress / program）
async function switchTab(page, tabKey) {
  const ok = await page.evaluate((k) => {
    const el = document.querySelector(`.tab[data-tab="${k}"]`);
    if (!el) return false;
    el.click();
    return true;
  }, tabKey);
  await sleep(1200);
  return ok;
}

async function navigateFresh(page) {
  // Firebase 接続で networkidle が来ないケースがあるので load + 十分な sleep で待つ
  await page.goto(BASE, { waitUntil: 'load', timeout: 60000 });
  // sample 注入は reload を伴うので追加で待つ
  await sleep(3500);
  // オンボーディング／ランディング画面（「ロードマップを始める」「スキップ」）が
  // 挟まる場合があるので自動で閉じる
  await page.evaluate(() => {
    // localStorage にオンボーディング完了フラグを立てる（旧アプリ互換）
    try {
      localStorage.setItem('onboarding_completed', '1');
      localStorage.setItem('cta_onboarding_v1', 'done');
      localStorage.setItem('cta_landing_seen', '1');
    } catch (_) {}
  });
  // 画面上に「スキップ」「ロードマップを始める」があれば押す
  const skipBtns = await page.$$('a, button');
  for (const b of skipBtns) {
    const txt = (await b.textContent() || '').trim();
    if (/^(スキップ|ロードマップを始める|Skip|→)/.test(txt) || /始める|スキップ/.test(txt)) {
      try { await b.click({ timeout: 1500 }); await sleep(1200); break; } catch(_) {}
    }
  }
  await sleep(1500);
}

async function shot(page, dir, name, prep) {
  if (prep) await prep(page);
  await sleep(500);
  await page.screenshot({ path: path.join(OUT, dir, `${name}.png`), fullPage: false });
  console.log(`  ✓ ${dir}/${name}.png`);
}

(async () => {
  const browser = await chromium.launch();

  // === モバイル ===
  console.log('📱 モバイル撮影 (375x812)');
  const mctx = await browser.newContext({
    viewport: { width: 375, height: 812 },
    deviceScaleFactor: 2,
  });
  const mpage = await mctx.newPage();
  await navigateFresh(mpage);

  // ① ホーム
  await shot(mpage, 'mobile', '01_home', async (p) => {
    await p.evaluate(() => window.scrollTo(0,0));
  });

  // ② 技アコーディオン展開
  await shot(mpage, 'mobile', '02_skills_accordion', async (p) => {
    await tryClickByText(p, /すべて開く/);
    await sleep(800);
    await p.evaluate(() => window.scrollTo(0, 500));
  });

  // ③ 技詳細（バク転）— skills タブ + バク転カードをクリック
  await shot(mpage, 'mobile', '03_skill_detail', async (p) => {
    await navigateFresh(p);
    await switchTab(p, 'skills');
    await sleep(800);
    const found = await p.evaluate(() => {
      // バク転カードを探す（複数の class 可能性）
      const cands = [...document.querySelectorAll('.skill-card, .skill-item, .skill-row, [class*="skill"]')];
      const t = cands.find(c => /バク転/.test(c.textContent || ''));
      if (t) { t.scrollIntoView({block:'center'}); t.click(); return 'skill-card'; }
      // フォールバック: h3/h4/.name 系
      const titles = [...document.querySelectorAll('h3, h4, .skill-name, .name')];
      const t2 = titles.find(e => e.textContent.trim() === 'バク転');
      if (t2) { const p2 = t2.closest('[class*="skill"], article, li, div'); (p2||t2).click(); return 'title'; }
      return false;
    });
    console.log('    skill detail click:', found);
    await sleep(1500);
    await p.evaluate(() => window.scrollTo(0, 0));
  });

  // ④ 練習メニュー — menu タブ
  await shot(mpage, 'mobile', '04_practice_menu', async (p) => {
    await navigateFresh(p);
    await switchTab(p, 'menu');
    await sleep(1200);
    await p.evaluate(() => {
      const pane = document.querySelector('#pane-menu, [data-pane="menu"]');
      if (pane) pane.scrollIntoView({block:'start'});
      else window.scrollTo(0, 400);
    });
    await sleep(400);
  });

  // ⑤ 成長記録（ヒートマップ）— progress タブ
  await shot(mpage, 'mobile', '05_progress_heatmap', async (p) => {
    await navigateFresh(p);
    await switchTab(p, 'progress');
    await sleep(1500);
    await p.evaluate(() => {
      const pane = document.querySelector('#pane-progress, [data-pane="progress"]');
      if (pane) pane.scrollIntoView({block:'start'});
      else window.scrollTo(0, 400);
    });
    await sleep(400);
  });

  // ⑥ 練習プログラム — program タブ + プログラム作成
  await shot(mpage, 'mobile', '06_program_circuit', async (p) => {
    await navigateFresh(p);
    await switchTab(p, 'program');
    await sleep(1200);
    // 「プログラムを作る」ボタンを直接クリック
    await p.evaluate(() => {
      const btn = [...document.querySelectorAll('button, [class*="btn"]')].find(b => /プログラム/.test(b.textContent || '') && /(作る|生成|作成)/.test(b.textContent || ''));
      if (btn) btn.click();
    });
    await sleep(1800);
    await p.evaluate(() => {
      const circuit = document.querySelector('.circuit-map, [class*="circuit"], svg');
      if (circuit) circuit.scrollIntoView({ block: 'center' });
      else window.scrollTo(0, 800);
    });
    await sleep(600);
  });

  await mctx.close();

  // === デスクトップ ===
  console.log('🖥️  デスクトップ撮影 (1280x900)');
  const dctx = await browser.newContext({
    viewport: { width: 1280, height: 900 },
    deviceScaleFactor: 2,
  });
  const dpage = await dctx.newPage();
  await navigateFresh(dpage);

  // 練習プログラム（コーチ機能・サーキット配置）
  await shot(dpage, 'desktop', '01_program_circuit', async (p) => {
    await switchTab(p, 'program');
    await sleep(1200);
    await p.evaluate(() => {
      const btn = [...document.querySelectorAll('button, [class*="btn"]')].find(b => /プログラム/.test(b.textContent || '') && /(作る|生成|作成)/.test(b.textContent || ''));
      if (btn) btn.click();
    });
    await sleep(2000);
    await p.evaluate(() => {
      const circuit = document.querySelector('.circuit-map, [class*="circuit"], svg');
      if (circuit) circuit.scrollIntoView({ block: 'center' });
      else window.scrollTo(0, 500);
    });
    await sleep(600);
  });

  // 成長記録ヒートマップ
  await shot(dpage, 'desktop', '02_progress_heatmap', async (p) => {
    await navigateFresh(p);
    await switchTab(p, 'progress');
    await sleep(1500);
    await p.evaluate(() => {
      const pane = document.querySelector('#pane-progress, [data-pane="progress"]');
      if (pane) pane.scrollIntoView({block:'start'});
      else window.scrollTo(0, 0);
    });
    await sleep(400);
  });

  await dctx.close();
  await browser.close();
  console.log('🎉 撮影完了');
})().catch(e => { console.error('❌ Error:', e); process.exit(1); });
