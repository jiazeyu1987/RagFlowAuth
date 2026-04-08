import { useEffect, useState } from 'react';
import operationApprovalApi from '../../features/operationApproval/api';
import { publishInboxUnreadCount, subscribeInboxUnreadCount } from '../../features/notification/inboxUnreadSync';

export const useInboxUnreadCount = (userId) => {
  const [inboxUnreadCount, setInboxUnreadCount] = useState(0);

  useEffect(
    () => subscribeInboxUnreadCount((nextCount) => {
      setInboxUnreadCount(nextCount);
    }),
    []
  );

  useEffect(() => {
    if (!userId) {
      setInboxUnreadCount(0);
      publishInboxUnreadCount(0);
      return undefined;
    }
    if (typeof window === 'undefined') return undefined;

    let cancelled = false;

    const loadInboxUnreadCount = async () => {
      try {
        const response = await operationApprovalApi.listInbox({ limit: 1 });
        if (cancelled) return;
        const nextCount = response.unreadCount;
        setInboxUnreadCount(nextCount);
        publishInboxUnreadCount(nextCount);
      } catch {
        if (cancelled) return;
        setInboxUnreadCount(0);
        publishInboxUnreadCount(0);
      }
    };

    loadInboxUnreadCount();
    const timerId = window.setInterval(loadInboxUnreadCount, 30000);

    return () => {
      cancelled = true;
      window.clearInterval(timerId);
    };
  }, [userId]);

  return inboxUnreadCount;
};
