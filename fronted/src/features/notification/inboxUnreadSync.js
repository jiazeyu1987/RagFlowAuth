const INBOX_UNREAD_COUNT_EVENT = 'notification:inbox-unread-count';

export const normalizeInboxUnreadCount = (value) => {
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric <= 0) return 0;
  return Math.floor(numeric);
};

export const publishInboxUnreadCount = (value) => {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new CustomEvent(INBOX_UNREAD_COUNT_EVENT, {
    detail: { unreadCount: normalizeInboxUnreadCount(value) },
  }));
};

export const subscribeInboxUnreadCount = (handler) => {
  if (typeof window === 'undefined') return () => {};
  const listener = (event) => {
    handler(normalizeInboxUnreadCount(event?.detail?.unreadCount));
  };
  window.addEventListener(INBOX_UNREAD_COUNT_EVENT, listener);
  return () => window.removeEventListener(INBOX_UNREAD_COUNT_EVENT, listener);
};

