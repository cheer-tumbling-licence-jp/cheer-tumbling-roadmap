/**
 * 不具合報告ウィジェット（共通モジュール）
 *
 * 使い方：
 *   <script src="coach/bug-report.js" defer></script>
 *
 * ページに以下を自動で追加：
 * - 右下フローティングボタン「🐛 不具合報告」
 * - クリックで開くモーダル（テキストエリア＋送信）
 * - Firestore の bug_reports コレクションに保存
 *
 * 依存：firebase-app-compat / firebase-firestore-compat / firebase-auth-compat が
 *      既に読み込まれている前提（initializeApp 済み）。
 */
(function setupBugReport() {
  'use strict';

  if (document.getElementById('bug-report-fab')) return;

  // === CSS ===
  const style = document.createElement('style');
  style.textContent = `
    #bug-report-fab {
      position: fixed;
      bottom: 16px;
      right: 16px;
      background: linear-gradient(135deg, #ff4d8f, #a855f7);
      color: white;
      border: none;
      border-radius: 999px;
      padding: 10px 16px;
      font-size: 12px;
      font-weight: 700;
      cursor: pointer;
      box-shadow: 0 4px 16px rgba(0,0,0,0.4);
      z-index: 500;
      font-family: -apple-system, "Hiragino Kaku Gothic ProN", sans-serif;
    }
    #bug-report-fab:hover { transform: translateY(-2px); }
    @media (max-width: 600px) {
      #bug-report-fab {
        bottom: 12px; right: 12px;
        padding: 8px 12px;
        font-size: 11px;
      }
    }
    #bug-report-modal-bg {
      position: fixed; inset: 0;
      background: rgba(0,0,0,0.7);
      z-index: 1000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 16px;
    }
    #bug-report-modal-bg.show { display: flex; }
    #bug-report-modal {
      background: #1a0f2e;
      border: 1px solid rgba(255,255,255,0.12);
      border-radius: 16px;
      padding: 24px;
      max-width: 460px;
      width: 100%;
      max-height: 90vh;
      overflow-y: auto;
      color: #f5f3ff;
      font-family: inherit;
    }
    #bug-report-modal h3 { font-size: 18px; margin-bottom: 6px; }
    #bug-report-modal .sub {
      font-size: 12px;
      color: #b8b3d6;
      margin-bottom: 18px;
    }
    #bug-report-modal label {
      display: block;
      font-size: 12px;
      color: #b8b3d6;
      margin: 12px 0 6px;
      font-weight: 600;
    }
    #bug-report-modal textarea, #bug-report-modal input[type=text] {
      width: 100%;
      background: rgba(0,0,0,0.3);
      border: 1px solid rgba(255,255,255,0.12);
      color: #f5f3ff;
      padding: 10px 14px;
      border-radius: 10px;
      font-size: 13px;
      font-family: inherit;
    }
    #bug-report-modal textarea { min-height: 100px; resize: vertical; }
    #bug-report-modal textarea:focus, #bug-report-modal input:focus {
      outline: none; border-color: #06d6f8;
    }
    #bug-report-modal .actions {
      display: flex; gap: 8px; margin-top: 16px;
    }
    #bug-report-modal .actions button {
      flex: 1; padding: 12px;
      border-radius: 10px;
      font-size: 13px;
      font-weight: 700;
      cursor: pointer;
      font-family: inherit;
    }
    #bug-report-modal .cancel {
      background: rgba(255,255,255,0.06);
      border: 1px solid rgba(255,255,255,0.12);
      color: #b8b3d6;
    }
    #bug-report-modal .send {
      background: linear-gradient(135deg, #ff4d8f, #a855f7);
      color: white;
      border: none;
    }
    #bug-report-modal .send:disabled { opacity: 0.5; cursor: not-allowed; }
    #bug-report-modal .err {
      background: rgba(255,77,143,0.1);
      border: 1px solid rgba(255,77,143,0.3);
      color: #fda4c5;
      padding: 10px;
      border-radius: 10px;
      font-size: 12px;
      margin-top: 12px;
      display: none;
    }
    #bug-report-modal .err.show { display: block; }
    #bug-report-modal .err.ok {
      background: rgba(74,222,128,0.1);
      border-color: rgba(74,222,128,0.3);
      color: #86efac;
    }
  `;
  document.head.appendChild(style);

  // === ボタン＆モーダル ===
  const fab = document.createElement('button');
  fab.id = 'bug-report-fab';
  fab.innerHTML = '🐛 不具合報告';
  fab.title = '気になったこと・うまく動かないことを開発者に伝える';
  document.body.appendChild(fab);

  const modal = document.createElement('div');
  modal.id = 'bug-report-modal-bg';
  modal.innerHTML = `
    <div id="bug-report-modal">
      <h3>🐛 不具合・要望を送る</h3>
      <div class="sub">画面の挙動でおかしいところ、使いにくいところ、追加してほしい機能を教えてください。<br>開発者（Claude）が確認してすぐ修正します。</div>
      <label for="br-title">タイトル（30文字以内）</label>
      <input type="text" id="br-title" maxlength="30" placeholder="例：課題が画面からはみ出る">
      <label for="br-body">詳しい内容</label>
      <textarea id="br-body" maxlength="2000" placeholder="例：iPhone Safari で開いたら、課題リストが横に切れて見えませんでした。スクロールで右側が見られず、報告ボタンも押せませんでした。"></textarea>
      <div class="err" id="br-msg"></div>
      <div class="actions">
        <button class="cancel" id="br-cancel">キャンセル</button>
        <button class="send" id="br-send">送信</button>
      </div>
    </div>
  `;
  document.body.appendChild(modal);

  function showMsg(ok, text) {
    const el = modal.querySelector('#br-msg');
    el.textContent = text;
    el.classList.add('show');
    if (ok) el.classList.add('ok'); else el.classList.remove('ok');
  }
  function clearMsg() {
    modal.querySelector('#br-msg').classList.remove('show', 'ok');
  }

  fab.onclick = () => {
    modal.classList.add('show');
    clearMsg();
    modal.querySelector('#br-title').value = '';
    modal.querySelector('#br-body').value = '';
    setTimeout(() => modal.querySelector('#br-title').focus(), 50);
  };
  modal.querySelector('#br-cancel').onclick = () => modal.classList.remove('show');
  modal.addEventListener('click', (e) => {
    if (e.target === modal) modal.classList.remove('show');
  });

  modal.querySelector('#br-send').onclick = async () => {
    clearMsg();
    const title = modal.querySelector('#br-title').value.trim();
    const body = modal.querySelector('#br-body').value.trim();
    if (!body) return showMsg(false, '内容を入力してください');

    const btn = modal.querySelector('#br-send');
    btn.disabled = true;
    const orig = btn.textContent;
    btn.textContent = '送信中…';

    try {
      // Firebase が初期化されている前提
      if (typeof firebase === 'undefined' || !firebase.apps.length) {
        return showMsg(false, 'Firebaseに接続できません。ページを再読み込みしてください。');
      }
      const auth = firebase.auth();
      const db = firebase.firestore();
      const user = auth.currentUser;

      await db.collection('bug_reports').add({
        title: title || '(タイトルなし)',
        body: body,
        userId: user ? user.uid : null,
        userEmail: user ? user.email : null,
        userDisplayName: user ? (user.displayName || '') : null,
        page: location.pathname,
        url: location.href,
        userAgent: navigator.userAgent,
        viewport: `${window.innerWidth}x${window.innerHeight}`,
        createdAt: firebase.firestore.FieldValue.serverTimestamp(),
        status: 'open'
      });

      showMsg(true, '✅ 報告ありがとうございました！すぐに確認します。');
      setTimeout(() => modal.classList.remove('show'), 1500);
    } catch (err) {
      console.error(err);
      showMsg(false, '送信に失敗しました：' + (err.message || err));
    } finally {
      btn.disabled = false;
      btn.textContent = orig;
    }
  };

  console.log('Bug report widget loaded.');
})();
