/**
 * Cheer Tumbling Roadmap - アプリ更新 & お知らせ
 *
 * 提供する機能：
 *   1. 画面右下に「⟳ アプリを更新」ボタンを設置
 *      - Service Worker をアンレジスター + Cache Storage を全削除 + リロード
 *      - キャッシュで古い画面が表示されている問題への根本解決
 *   2. 画面上部にお知らせバナーを表示
 *      - data/announcements.json から最新の未読を取得
 *      - 既読は localStorage に保存（id 単位）
 *      - 期限切れ（expiresAt）の項目は表示しない
 *
 * 各 HTML から <script src="/app-update.js" defer></script> で読み込む。
 */
(function appUpdateBanner() {
  'use strict';

  const READ_KEY = 'cta_announcement_read_v1';

  // ============ 1. 「⟳ アプリを更新」FAB ============
  function createUpdateButton() {
    if (document.getElementById('app-update-fab')) return;
    const btn = document.createElement('button');
    btn.id = 'app-update-fab';
    btn.type = 'button';
    btn.setAttribute('aria-label', 'アプリを最新版に更新する');
    btn.title = 'アプリを最新版に更新';
    btn.innerHTML = '⟳';
    btn.style.cssText = [
      'position:fixed', 'bottom:16px', 'right:16px',
      'width:44px', 'height:44px',
      'border-radius:50%', 'border:none',
      'background:linear-gradient(135deg,#06d6f8,#a78bfa)',
      'color:white', 'font-size:20px', 'font-weight:800',
      'cursor:pointer', 'z-index:9999',
      'box-shadow:0 4px 12px rgba(0,0,0,0.3)',
      'transition:transform .15s',
      'font-family:inherit',
    ].join(';');
    btn.onmouseenter = () => { btn.style.transform = 'scale(1.08) rotate(180deg)'; };
    btn.onmouseleave = () => { btn.style.transform = 'scale(1) rotate(0)'; };
    btn.onclick = async () => {
      if (!confirm('アプリを最新版に更新しますか？\n（古いキャッシュを削除して読み直します。ログイン状態は維持されます）')) return;
      btn.disabled = true;
      btn.innerHTML = '…';
      try {
        if ('serviceWorker' in navigator) {
          const regs = await navigator.serviceWorker.getRegistrations();
          await Promise.all(regs.map(r => r.unregister()));
        }
        if ('caches' in window) {
          const keys = await caches.keys();
          await Promise.all(keys.map(k => caches.delete(k)));
        }
      } catch (e) {
        console.warn('cache clear エラー:', e);
      } finally {
        // クエリ ?_=タイムスタンプ を付けてリロード（HTML 自体もキャッシュ無効化）
        const u = new URL(location.href);
        u.searchParams.set('_t', Date.now().toString());
        location.replace(u.toString());
      }
    };
    document.body.appendChild(btn);
  }

  // ============ 2. お知らせバナー ============
  function getReadIds() {
    try { return JSON.parse(localStorage.getItem(READ_KEY) || '[]'); }
    catch (e) { return []; }
  }
  function markRead(id) {
    const ids = getReadIds();
    if (!ids.includes(id)) ids.push(id);
    try { localStorage.setItem(READ_KEY, JSON.stringify(ids)); } catch (e) {}
  }
  function isExpired(item) {
    if (!item.expiresAt) return false;
    const exp = new Date(item.expiresAt + 'T23:59:59');
    return exp < new Date();
  }
  function levelColor(level) {
    switch (level) {
      case 'warn':    return { bg: 'rgba(255,210,63,0.15)', border: 'rgba(255,210,63,0.5)', fg: '#ffd23f' };
      case 'danger':  return { bg: 'rgba(255,77,143,0.15)', border: 'rgba(255,77,143,0.5)', fg: '#ff4d8f' };
      case 'success': return { bg: 'rgba(74,222,128,0.15)', border: 'rgba(74,222,128,0.5)', fg: '#4ade80' };
      default:        return { bg: 'rgba(6,214,248,0.12)',  border: 'rgba(6,214,248,0.45)', fg: '#06d6f8' };
    }
  }
  function escapeHtml(s) {
    return String(s||'').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  }
  function showBanner(item) {
    if (document.getElementById('app-announcement-banner')) return;
    const c = levelColor(item.level);
    const wrap = document.createElement('div');
    wrap.id = 'app-announcement-banner';
    wrap.style.cssText = [
      'position:fixed', 'top:0', 'left:0', 'right:0',
      'z-index:9998', 'padding:12px 16px',
      'background:' + c.bg, 'border-bottom:1px solid ' + c.border,
      'color:#fff', 'backdrop-filter:blur(8px)', '-webkit-backdrop-filter:blur(8px)',
      'font-family:inherit', 'font-size:13px', 'line-height:1.5',
      'animation:slideDown .35s ease-out',
    ].join(';');
    const style = document.createElement('style');
    style.textContent = '@keyframes slideDown { from { transform:translateY(-100%); } to { transform:translateY(0); } }';
    document.head.appendChild(style);
    wrap.innerHTML = `
      <div style="max-width:720px;margin:0 auto;display:flex;gap:10px;align-items:flex-start;">
        <div style="flex-shrink:0;color:${c.fg};font-size:18px;line-height:1;">📢</div>
        <div style="flex:1;min-width:0;">
          <div style="font-weight:800;color:${c.fg};margin-bottom:4px;">${escapeHtml(item.title || 'お知らせ')}</div>
          <div style="color:#fff;opacity:0.92;white-space:pre-wrap;">${escapeHtml(item.body || '')}</div>
          ${item.link ? `<a href="${escapeHtml(item.link)}" target="_blank" rel="noopener" style="color:${c.fg};text-decoration:underline;display:inline-block;margin-top:6px;font-weight:700;">${escapeHtml(item.linkText || '詳しく見る →')}</a>` : ''}
        </div>
        <button type="button" id="app-announcement-close" aria-label="閉じる" style="flex-shrink:0;background:transparent;border:none;color:#fff;font-size:20px;cursor:pointer;padding:0 4px;line-height:1;opacity:0.7;">×</button>
      </div>
    `;
    document.body.appendChild(wrap);
    wrap.querySelector('#app-announcement-close').onclick = () => {
      markRead(item.id);
      wrap.style.transition = 'transform .25s, opacity .25s';
      wrap.style.transform = 'translateY(-100%)';
      wrap.style.opacity = '0';
      setTimeout(() => wrap.remove(), 250);
    };
  }
  async function loadAnnouncements() {
    try {
      const res = await fetch('data/announcements.json', { cache: 'no-cache' });
      if (!res.ok) return;
      const data = await res.json();
      const items = (data && data.items) || [];
      const readIds = getReadIds();
      // 未読 & 期限内 のうち、最新の1件のみ表示
      const candidates = items
        .filter(it => it && it.id)
        .filter(it => !readIds.includes(it.id))
        .filter(it => !isExpired(it))
        .sort((a, b) => (b.createdAt || '').localeCompare(a.createdAt || ''));
      if (candidates.length > 0) showBanner(candidates[0]);
    } catch (e) {
      console.warn('announcements 読み込み失敗:', e);
    }
  }

  // ============ 起動 ============
  function init() {
    createUpdateButton();
    loadAnnouncements();
    autoSwVersionCheck();
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // ============ 3. SW バージョン自動チェック（セッション初回） ============
  // GitHub Pages が service-worker.js に max-age=600 を付けるため、
  // 通常の reg.update() では最大10分間 古い SW が使われ続ける。
  // セッション初回だけ sw.js を no-store で直接フェッチして CACHE_VERSION を比較、
  // 古ければ Cache 全削除＋SW unregister＋リロードで強制的に最新版へ切替える。
  function autoSwVersionCheck() {
    if (!('serviceWorker' in navigator)) return;
    // 同一セッション内は 1 回だけ実行（頻度制御）
    try {
      if (sessionStorage.getItem('sw_ver_checked')) return;
      sessionStorage.setItem('sw_ver_checked', '1');
    } catch (_) { /* private mode 等では通過 */ }

    Promise.all([
      caches.keys(),
      fetch('/service-worker.js', { cache: 'no-store' }).then(r => r.text()),
    ]).then(([cacheKeys, swText]) => {
      const match = swText.match(/CACHE_VERSION\s*=\s*['"]([^'"]+)['"]/);
      if (!match) return;
      const latest = match[1];
      const current = cacheKeys.find(k => k.startsWith('cheer-tumbling-'));
      const currentVer = current ? current.replace('cheer-tumbling-', '') : null;
      if (!currentVer || currentVer === latest) return;

      console.log('[app-update] 新バージョン検出:', currentVer, '→', latest, '。強制更新します。');
      Promise.all(cacheKeys.map(k => caches.delete(k)))
        .then(() => navigator.serviceWorker.getRegistrations())
        .then(regs => Promise.all(regs.map(r => r.unregister())))
        .then(() => {
          // 目立つ通知を1秒だけ出してから自動リロード
          const banner = document.createElement('div');
          banner.style.cssText = 'position:fixed;top:0;left:0;right:0;background:linear-gradient(135deg,#06d6f8,#a78bfa);color:white;padding:12px 16px;text-align:center;font-weight:800;z-index:99999;font-size:14px;box-shadow:0 4px 12px rgba(0,0,0,0.3);';
          banner.textContent = `🔄 新バージョン ${latest} に更新中…`;
          document.body.appendChild(banner);
          setTimeout(() => window.location.reload(), 800);
        });
    }).catch(err => console.warn('[app-update] SW version check failed:', err));
  }
})();
