/* nav-msg-badge.js — shared unread-count updater for the nav "Messages" badge.
 *
 * Drops into any page that already renders <span id="nav-msg-badge"> in the nav.
 * Strategy:
 *   1. Initial fetch on load.
 *   2. Open a WebSocket to /ws/dm — bumps the count instantly when a message
 *      arrives, decrements when the active /messages tab issues a read.
 *   3. Lightweight 5s polling as a fallback if the WS is closed.
 *   4. Re-fetch when the tab becomes visible again (tab switch / wake).
 *   5. BroadcastChannel: when the /messages page marks a thread read, every
 *      other open tab's badge updates immediately.
 *
 * Safe to include multiple times — guards against double-init.
 */
(function () {
  if (window.__qlNavMsgBadgeInit) return;
  window.__qlNavMsgBadgeInit = true;

  let unread = 0;
  let ws = null;
  let wsRetryMs = 1000;
  let pollTimer = null;
  let bcChan = null;

  function getBadge() {
    return document.getElementById('nav-msg-badge');
  }

  function applyBadge(n) {
    unread = Math.max(0, Number(n) || 0);
    const b = getBadge();
    if (!b) return;
    if (unread > 0) {
      b.textContent = unread > 99 ? '99+' : String(unread);
      b.style.display = '';
    } else {
      b.style.display = 'none';
    }
  }

  async function refresh() {
    try {
      const r = await fetch('/api/dm/unread-count', { credentials: 'include' });
      if (!r.ok) return;
      const d = await r.json();
      applyBadge(d.unread || 0);
    } catch (e) { /* swallow */ }
  }

  function connectWS() {
    try { if (ws) ws.close(); } catch (e) {}
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    try {
      ws = new WebSocket(`${proto}://${location.host}/ws/dm`);
    } catch (e) { return; }
    ws.onopen = () => { wsRetryMs = 1000; };
    ws.onmessage = (ev) => {
      let data;
      try { data = JSON.parse(ev.data); } catch (e) { return; }
      if (data.type === 'message') {
        const msg = data.message || {};
        // Server delivers two payloads: one with from_me=false to the recipient,
        // one with from_me=true to the sender's other tabs. Only count the
        // recipient-side delivery as a new unread, and only if the user isn't
        // currently looking at /messages (that page marks as read on open).
        if (msg.from_me === false && location.pathname !== '/messages') {
          applyBadge(unread + 1);
        }
      } else if (data.type === 'read_self') {
        // Custom signal: badge should refresh because *this user* (perhaps in
        // another tab) just read messages. We just refetch from server.
        refresh();
      }
    };
    ws.onclose = () => {
      ws = null;
      setTimeout(connectWS, wsRetryMs);
      wsRetryMs = Math.min(wsRetryMs * 2, 15000);
    };
    ws.onerror = () => { try { ws.close(); } catch (e) {} };
  }

  function startPolling() {
    // Fallback poll every 5s. Cheap endpoint, keeps badge fresh even if WS
    // is wedged or the proxy strips upgrades.
    if (pollTimer) clearTimeout(pollTimer);
    const tick = async () => {
      await refresh();
      pollTimer = setTimeout(tick, 5000);
    };
    pollTimer = setTimeout(tick, 5000);
  }

  function setupBroadcastChannel() {
    if (typeof BroadcastChannel === 'undefined') return;
    try {
      bcChan = new BroadcastChannel('ql-dm');
      bcChan.onmessage = (ev) => {
        const d = ev.data || {};
        if (d.type === 'unread') applyBadge(d.unread);
        else if (d.type === 'read') refresh();
      };
    } catch (e) {}
  }

  // Re-fetch when tab becomes visible (covers laptop wake / tab switch)
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) refresh();
  });

  // Boot: wait for badge element to exist (some pages inject the nav via JS),
  // then start everything.
  function boot() {
    if (!getBadge()) {
      // Try again shortly — gives client-side nav builders time to render
      setTimeout(boot, 200);
      return;
    }
    refresh();
    connectWS();
    startPolling();
    setupBroadcastChannel();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  // Expose helpers so the messages page can broadcast read events
  window.qlNavBadge = {
    refresh,
    set:    applyBadge,
    notifyRead() {
      try { if (bcChan) bcChan.postMessage({ type: 'read' }); } catch (e) {}
      refresh();
    },
    notifyUnread(n) {
      try { if (bcChan) bcChan.postMessage({ type: 'unread', unread: n }); } catch (e) {}
      applyBadge(n);
    },
  };
})();
