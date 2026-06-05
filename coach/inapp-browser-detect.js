/**
 * 内蔵ブラウザ（WebView）検出 & 外部ブラウザへの誘導
 *
 * Google OAuth は LINE / Instagram / X(Twitter) / Facebook 等の内蔵ブラウザでは
 * disallowed_useragent (403) でブロックされる。
 * このスクリプトはそれを検出し、ユーザーに「外部ブラウザで開いてください」と案内する。
 *
 * 対応：
 * - LINE: `?openExternalBrowser=1` を付けて再アクセス（LINE自動でSafari/Chromeを開く）
 * - その他：右上メニューから「ブラウザで開く」を案内
 */
(function detectInappBrowser() {
  'use strict';

  if (document.getElementById('iab-banner')) return;

  const ua = navigator.userAgent || '';
  const isLine = /Line\//i.test(ua);
  const isFB = /FBAN|FBAV/i.test(ua);
  const isInsta = /Instagram/i.test(ua);
  const isTwitter = /TwitterAndroid|Twitter for/i.test(ua);
  const isInappAny = isLine || isFB || isInsta || isTwitter ||
    // Android WebView 一般検出（Version/x.x が無く、Chrome がついてるパターン等）
    /; wv\)/i.test(ua);

  if (!isInappAny) return;

  // 既に外部ブラウザフラグ付きで開かれていれば、二重案内は出さない
  try {
    const params = new URLSearchParams(location.search);
    if (params.get('openExternalBrowser') === '1' && isLine) {
      // LINE が外部ブラウザを開くフロー中、すでに対処済みのはず
      return;
    }
  } catch (e) {}

  const appName = isLine ? 'LINE'
                : isFB ? 'Facebook'
                : isInsta ? 'Instagram'
                : isTwitter ? 'Twitter (X)'
                : 'アプリ内ブラウザ';

  // バナー＋詳細モーダル
  const style = document.createElement('style');
  style.textContent = `
    #iab-banner {
      position: fixed;
      top: 0; left: 0; right: 0;
      background: linear-gradient(135deg, #ff4d8f, #a855f7);
      color: white;
      padding: 12px 14px 12px 14px;
      z-index: 9999;
      font-family: -apple-system, "Hiragino Kaku Gothic ProN", sans-serif;
      box-shadow: 0 4px 16px rgba(0,0,0,0.4);
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 13px;
      line-height: 1.5;
    }
    #iab-banner .ic { font-size: 22px; flex-shrink: 0; }
    #iab-banner .msg { flex: 1; }
    #iab-banner .msg strong { display: block; font-weight: 800; margin-bottom: 2px; }
    #iab-banner .open-btn {
      background: white;
      color: #a855f7;
      border: none;
      padding: 8px 14px;
      border-radius: 8px;
      font-weight: 800;
      font-size: 12px;
      cursor: pointer;
      flex-shrink: 0;
      font-family: inherit;
    }
    #iab-banner .close-btn {
      background: transparent;
      border: none;
      color: rgba(255,255,255,0.7);
      font-size: 18px;
      cursor: pointer;
      padding: 0 4px;
      flex-shrink: 0;
    }
    #iab-modal-bg {
      position: fixed; inset: 0;
      background: rgba(0,0,0,0.8);
      z-index: 10000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }
    #iab-modal-bg.show { display: flex; }
    #iab-modal {
      background: #1a0f2e;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 16px;
      padding: 24px;
      max-width: 460px;
      width: 100%;
      color: #f5f3ff;
      max-height: 90vh;
      overflow-y: auto;
      font-family: -apple-system, "Hiragino Kaku Gothic ProN", sans-serif;
    }
    #iab-modal h3 { font-size: 18px; margin-bottom: 8px; }
    #iab-modal .lead { font-size: 13px; color: #b8b3d6; margin-bottom: 16px; line-height: 1.6; }
    #iab-modal .step {
      background: rgba(255,255,255,0.04);
      border: 1px solid rgba(255,255,255,0.1);
      border-radius: 10px;
      padding: 12px 14px;
      margin-bottom: 10px;
    }
    #iab-modal .step-num {
      background: linear-gradient(135deg, #06d6f8, #a855f7);
      color: white;
      width: 22px; height: 22px;
      border-radius: 50%;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      font-size: 12px;
      font-weight: 800;
      margin-right: 8px;
    }
    #iab-modal .url-box {
      background: rgba(0,0,0,0.3);
      border: 1px solid rgba(255,255,255,0.12);
      padding: 10px;
      border-radius: 8px;
      font-family: 'SF Mono', Menlo, monospace;
      font-size: 12px;
      color: #06d6f8;
      word-break: break-all;
      margin-top: 8px;
    }
    #iab-modal .actions {
      display: flex; gap: 8px; margin-top: 16px;
    }
    #iab-modal .actions button {
      flex: 1; padding: 12px;
      border-radius: 10px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      font-family: inherit;
    }
    #iab-modal .close {
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.12);
      color: #b8b3d6;
    }
    #iab-modal .copy {
      background: linear-gradient(135deg, #06d6f8, #a855f7);
      color: white;
      border: none;
    }
  `;
  document.head.appendChild(style);

  // バナー（常時表示）
  const banner = document.createElement('div');
  banner.id = 'iab-banner';
  banner.innerHTML = `
    <span class="ic">⚠️</span>
    <div class="msg">
      <strong>${appName} 内ブラウザではGoogleログインができません</strong>
      Safari / Chrome で開いてください
    </div>
    <button class="open-btn" id="iab-open-btn">開き方</button>
    <button class="close-btn" id="iab-close-banner">×</button>
  `;
  document.body.appendChild(banner);

  // 詳細モーダル
  const modal = document.createElement('div');
  modal.id = 'iab-modal-bg';
  const currentUrl = location.href;
  const cleanUrl = currentUrl.split('?')[0].split('#')[0];

  // LINE 専用の自動オープン URL
  const lineExternalUrl = currentUrl + (currentUrl.includes('?') ? '&' : '?') + 'openExternalBrowser=1';

  let lineSpecificSection = '';
  if (isLine) {
    lineSpecificSection = `
      <div class="step" style="background: linear-gradient(135deg, rgba(6,199,85,0.12), rgba(168,85,247,0.12)); border-color: rgba(6,199,85,0.4);">
        <strong style="color: #06c755;">💡 一番カンタンな方法</strong>
        <div style="font-size:12px;color:#b8b3d6;margin:6px 0 8px;">下のボタンを長押し → 「ブラウザで開く」を選ぶ</div>
        <a href="${lineExternalUrl}" style="display:block;background:#06c755;color:white;text-align:center;padding:10px;border-radius:8px;text-decoration:none;font-weight:700;font-size:13px;">🌐 Safari/Chrome で開く</a>
      </div>
    `;
  }

  modal.innerHTML = `
    <div id="iab-modal">
      <h3>🌐 外部ブラウザで開く必要があります</h3>
      <div class="lead">
        Google アカウントでログインするには、Safari / Chrome / Firefox など標準のブラウザで開く必要があります（${appName} の内蔵ブラウザでは Google のセキュリティ仕様で利用できません）。
      </div>

      ${lineSpecificSection}

      <div class="step">
        <span class="step-num">1</span><strong>右上の「︙」または「⋯」ボタンをタップ</strong>
        <div style="font-size:12px;color:#b8b3d6;margin-top:4px;">画面の右上角にある縦3点または横3点のメニュー</div>
      </div>
      <div class="step">
        <span class="step-num">2</span><strong>「ブラウザで開く」「Safariで開く」「Chromeで開く」 を選ぶ</strong>
        <div style="font-size:12px;color:#b8b3d6;margin-top:4px;">表記はアプリにより異なります</div>
      </div>
      <div class="step">
        <span class="step-num">3</span><strong>開いたブラウザでログインを完了</strong>
      </div>

      <div style="margin-top: 16px;">
        <div style="font-size: 11px; color: #b8b3d6; margin-bottom: 4px;">URL をコピーして手動でブラウザに貼り付けることもできます：</div>
        <div class="url-box" id="iab-url-box">${cleanUrl}</div>
      </div>

      <div class="actions">
        <button class="close" id="iab-close-modal">閉じる</button>
        <button class="copy" id="iab-copy-btn">📋 URLをコピー</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  // ハンドラ
  document.getElementById('iab-open-btn').onclick = () => modal.classList.add('show');
  document.getElementById('iab-close-banner').onclick = () => banner.style.display = 'none';
  document.getElementById('iab-close-modal').onclick = () => modal.classList.remove('show');
  modal.addEventListener('click', (e) => { if (e.target === modal) modal.classList.remove('show'); });
  document.getElementById('iab-copy-btn').onclick = async () => {
    try {
      await navigator.clipboard.writeText(cleanUrl);
      document.getElementById('iab-copy-btn').textContent = '✓ コピーしました';
      setTimeout(() => { document.getElementById('iab-copy-btn').textContent = '📋 URLをコピー'; }, 2000);
    } catch (e) {
      // クリップボード API が使えない場合のフォールバック
      const box = document.getElementById('iab-url-box');
      const range = document.createRange();
      range.selectNode(box);
      window.getSelection().removeAllRanges();
      window.getSelection().addRange(range);
      try { document.execCommand('copy'); document.getElementById('iab-copy-btn').textContent = '✓ コピーしました'; }
      catch (e2) { alert('コピーできませんでした。URLを長押しで選択してコピーしてください。'); }
    }
  };

  // バナー分のスペースを上部に確保（コンテンツが隠れないように）
  document.body.style.paddingTop = (banner.offsetHeight) + 'px';

  console.warn('[InApp Browser Detected]', appName);
})();
