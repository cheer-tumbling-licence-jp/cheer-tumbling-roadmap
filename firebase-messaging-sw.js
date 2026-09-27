// Firebase Cloud Messaging Service Worker
// このファイルは https://roadmap.cheer-tumbling.jp/firebase-messaging-sw.js に配置される必要がある
// FCM はこのファイルをブラウザに登録して、バックグラウンド Push を受信する

importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.14.1/firebase-messaging-compat.js');

firebase.initializeApp({
  apiKey: "AIzaSyApucHjGGTbd5aAJFaKw_kwvCsm2EyRiSE",
  authDomain: "cheer-tumbling-roadmap.firebaseapp.com",
  projectId: "cheer-tumbling-roadmap",
  storageBucket: "cheer-tumbling-roadmap.firebasestorage.app",
  messagingSenderId: "1012752519800",
  appId: "1:1012752519800:web:a393d04fced850edac938d"
});

const messaging = firebase.messaging();

// バックグラウンド Push を受信
messaging.onBackgroundMessage(async (payload) => {
  console.log('[FCM SW] バックグラウンド Push 受信:', payload);

  const badgeCount = parseInt(payload.data?.badgeCount || '0', 10);
  // Badge API でホーム画面アイコンに数字表示
  if (self.navigator && self.navigator.setAppBadge && badgeCount > 0) {
    try { await self.navigator.setAppBadge(badgeCount); } catch (e) { console.warn('setAppBadge fail:', e); }
  }

  // 通知バナー表示（音・振動付き）
  const title = payload.notification?.title || payload.data?.title || '🎀 新着通知';
  const body  = payload.notification?.body  || payload.data?.body  || '新しい提出があります';
  const clickUrl = payload.data?.clickUrl || '/coach.html';

  await self.registration.showNotification(title, {
    body,
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-192.png',
    tag: 'cta-notification',
    renotify: true,
    data: { clickUrl },
    requireInteraction: false
  });
});

// 通知バナーをタップした時の遷移
self.addEventListener('notificationclick', (event) => {
  event.notification.close();
  const url = event.notification.data?.clickUrl || '/';
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then(list => {
      // 既に開いているタブがあればフォーカス
      for (const c of list) {
        if (c.url.includes(url) && 'focus' in c) return c.focus();
      }
      // 無ければ新規タブで開く
      if (self.clients.openWindow) return self.clients.openWindow(url);
    })
  );
});
