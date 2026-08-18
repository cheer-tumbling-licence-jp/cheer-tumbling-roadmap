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
    const els = [...document.querySelectorAll('button, a, [role="tab"]')];
    return els.find(e => re.test(e.textContent || ''));
  }, regex.source);
  const el = handle.asElement();
  if (!el) throw new Error(`element not found: ${regex}`);
  await el.click();
  await sleep(600);
}

async function tryClickByText(page, regex) {
  try { await clickByText(page, regex); return true; }
  catch(e) { console.log('  ! skip:', regex.source); return false; }
}

async function navigateFresh(page) {
  await page.goto(BASE, { waitUntil: 'networkidle' });
  // sample 注入は reload を伴うので追加で待つ
  await sleep(2500);
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

  // ③ 技詳細（バク転）
  await shot(mpage, 'mobile', '03_skill_detail', async (p) => {
    await navigateFresh(p);
    await tryClickByText(p, /タンブリング技/);
    await tryClickByText(p, /すべて開く/);
    await sleep(500);
    const found = await p.evaluate(() => {
      const cards = [...document.querySelectorAll('.skill-card, .skill-item, [class*="card"]')];
      const target = cards.find(c => /^バク転|^バク転$/.test((c.querySelector('.skill-name, h3, h4')||c).textContent || ''));
      if (target) { target.click(); return true; }
      // フォールバック: テキスト「バク転」を含むタイトル要素
      const titles = [...document.querySelectorAll('h3, h4, .skill-name, .name')];
      const t2 = titles.find(e => e.textContent.trim() === 'バク転');
      if (t2) { t2.click(); return 'fallback'; }
      return false;
    });
    console.log('    skill detail click:', found);
    await sleep(1200);
    await p.evaluate(() => window.scrollTo(0,0));
  });

  // ④ 練習メニュー
  await shot(mpage, 'mobile', '04_practice_menu', async (p) => {
    await navigateFresh(p);
    await tryClickByText(p, /練習メニュー/);
    await sleep(1000);
    await p.evaluate(() => window.scrollTo(0,0));
  });

  // ⑤ 成長記録（ヒートマップ）
  await shot(mpage, 'mobile', '05_progress_heatmap', async (p) => {
    await navigateFresh(p);
    await tryClickByText(p, /成長記録/);
    await sleep(1500);
    await p.evaluate(() => window.scrollTo(0,0));
  });

  // ⑥ 練習プログラム（生成後・サーキット配置）
  await shot(mpage, 'mobile', '06_program_circuit', async (p) => {
    await navigateFresh(p);
    await tryClickByText(p, /練習プログラム/);
    await sleep(1000);
    await tryClickByText(p, /プログラムを作る|プログラム作成|作成/);
    await sleep(1500);
    // 生成された配置図にスクロール
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
    await tryClickByText(p, /練習プログラム/);
    await sleep(1500);
    await tryClickByText(p, /プログラムを作る|プログラム作成/);
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
    await tryClickByText(p, /成長記録/);
    await sleep(1500);
    await p.evaluate(() => window.scrollTo(0,0));
  });

  await dctx.close();
  await browser.close();
  console.log('🎉 撮影完了');
})().catch(e => { console.error('❌ Error:', e); process.exit(1); });
