import { useCallback, useEffect, useState } from 'react';

export default function useSearchHistory(storageKey, limit = 10) {
  const [history, setHistory] = useState([]);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      const parsed = JSON.parse(raw || '[]');
      if (!Array.isArray(parsed)) {
        setHistory([]);
        return;
      }
      setHistory(
        parsed
          .filter((item) => typeof item === 'string')
          .map((item) => item.trim())
          .filter(Boolean)
          .slice(0, limit)
      );
    } catch {
      setHistory([]);
    }
  }, [limit, storageKey]);

  const persist = useCallback(
    (items) => {
      const nextItems = Array.isArray(items) ? items.slice(0, limit) : [];
      setHistory(nextItems);
      try {
        window.localStorage.setItem(storageKey, JSON.stringify(nextItems));
      } catch {
      }
    },
    [limit, storageKey]
  );

  const pushHistory = useCallback(
    (query) => {
      const value = String(query || '').trim();
      if (!value) return;
      persist([value, ...history.filter((item) => item !== value)]);
    },
    [history, persist]
  );

  const clearHistory = useCallback(() => {
    persist([]);
  }, [persist]);

  const removeHistoryItem = useCallback(
    (query) => {
      const value = String(query || '').trim();
      if (!value) return;
      persist(history.filter((item) => item !== value));
    },
    [history, persist]
  );

  return {
    history,
    pushHistory,
    clearHistory,
    removeHistoryItem,
  };
}
