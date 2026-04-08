import { useCallback, useEffect, useMemo, useState } from 'react';

const RECENT_KEY_PREFIX = 'ragflowauth_recent_dataset_keywords_v1';
const USAGE_KEY_PREFIX = 'ragflowauth_browser_dataset_usage_v1';

const buildStorageKey = (prefix, userId) => `${prefix}:${userId || 'anon'}`;

const readStorageJson = (key, fallbackValue) => {
  if (typeof window === 'undefined') return fallbackValue;
  try {
    const raw = window.localStorage.getItem(key);
    return raw ? JSON.parse(raw) : fallbackValue;
  } catch {
    return fallbackValue;
  }
};

const writeStorageJson = (key, value) => {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // ignore storage errors
  }
};

const normalizeRecentKeywords = (values) =>
  Array.isArray(values)
    ? values
        .filter((value) => typeof value === 'string' && value.trim())
        .slice(0, 5)
    : [];

const normalizeUsageCounts = (raw) => {
  if (!raw || typeof raw !== 'object' || Array.isArray(raw)) return {};

  const normalized = {};
  Object.entries(raw).forEach(([key, value]) => {
    const count = Number(value || 0);
    if (key && Number.isFinite(count) && count > 0) normalized[key] = count;
  });
  return normalized;
};

export default function useDocumentBrowserPreferences({ userId, datasetsWithFolders }) {
  const [datasetFilterKeyword, setDatasetFilterKeyword] = useState('');
  const [recentDatasetKeywords, setRecentDatasetKeywords] = useState([]);
  const [datasetUsageCounts, setDatasetUsageCounts] = useState({});

  const recentStorageKey = useMemo(
    () => buildStorageKey(RECENT_KEY_PREFIX, userId),
    [userId]
  );
  const usageStorageKey = useMemo(
    () => buildStorageKey(USAGE_KEY_PREFIX, userId),
    [userId]
  );

  useEffect(() => {
    setRecentDatasetKeywords(
      normalizeRecentKeywords(readStorageJson(recentStorageKey, []))
    );
  }, [recentStorageKey]);

  useEffect(() => {
    setDatasetUsageCounts(normalizeUsageCounts(readStorageJson(usageStorageKey, {})));
  }, [usageStorageKey]);

  const recordDatasetUsage = useCallback(
    (datasetName) => {
      const name = String(datasetName || '').trim();
      if (!name) return;

      setDatasetUsageCounts((previous) => {
        const next = {
          ...(previous || {}),
          [name]: Number(previous?.[name] || 0) + 1,
        };
        writeStorageJson(usageStorageKey, next);
        return next;
      });
    },
    [usageStorageKey]
  );

  const commitKeyword = useCallback(
    (value) => {
      const keyword = String(value || '').trim();
      if (!keyword) return;

      const next = [keyword, ...recentDatasetKeywords]
        .filter(Boolean)
        .filter(
          (item, idx, list) =>
            list.findIndex(
              (candidate) => candidate.toLowerCase() === item.toLowerCase()
            ) === idx
        )
        .slice(0, 5);

      setRecentDatasetKeywords(next);
      writeStorageJson(recentStorageKey, next);
    },
    [recentDatasetKeywords, recentStorageKey]
  );

  const quickDatasets = useMemo(() => {
    const counts = datasetUsageCounts || {};
    return [...datasetsWithFolders]
      .sort((a, b) => {
        const countA = Number(counts[a.name] || 0);
        const countB = Number(counts[b.name] || 0);
        if (countA !== countB) return countB - countA;
        return String(a.name || '').localeCompare(String(b.name || ''), 'zh-Hans-CN');
      })
      .slice(0, 10);
  }, [datasetUsageCounts, datasetsWithFolders]);

  return {
    datasetFilterKeyword,
    setDatasetFilterKeyword,
    recentDatasetKeywords,
    datasetUsageCounts,
    quickDatasets,
    recordDatasetUsage,
    commitKeyword,
  };
}
