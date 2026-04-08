import { useCallback, useEffect, useState } from 'react';

import { clampLimit } from './downloadPageUtils';

export default function useDownloadControllerConfig({
  storageKey,
  defaultSources,
  sourceLabelMap,
}) {
  const [keywordText, setKeywordText] = useState('');
  const [useAnd, setUseAnd] = useState(true);
  const [autoAnalyze, setAutoAnalyze] = useState(false);
  const [sources, setSources] = useState(defaultSources);
  const [configReady, setConfigReady] = useState(false);

  const updateSource = useCallback((key, patch) => {
    setSources((previous) => ({
      ...previous,
      [key]: { ...(previous[key] || {}), ...patch },
    }));
  }, []);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(storageKey);
      if (!raw) return;
      const parsed = JSON.parse(raw);
      if (typeof parsed?.keywordText === 'string') setKeywordText(parsed.keywordText);
      if (typeof parsed?.useAnd === 'boolean') setUseAnd(parsed.useAnd);
      if (typeof parsed?.autoAnalyze === 'boolean') setAutoAnalyze(parsed.autoAnalyze);
      if (parsed?.sources && typeof parsed.sources === 'object') {
        const next = {};
        Object.keys(sourceLabelMap).forEach((key) => {
          const cfg = parsed.sources[key] || {};
          const fallback = defaultSources[key] || { enabled: false, limit: 30 };
          next[key] = {
            enabled:
              typeof cfg.enabled === 'boolean'
                ? cfg.enabled
                : Boolean(fallback.enabled),
            limit: clampLimit(cfg.limit ?? fallback.limit),
          };
        });
        setSources(next);
      }
    } catch (_) {
      // ignore invalid cache
    } finally {
      setConfigReady(true);
    }
  }, [defaultSources, sourceLabelMap, storageKey]);

  useEffect(() => {
    if (!configReady) return;
    try {
      window.localStorage.setItem(
        storageKey,
        JSON.stringify({ keywordText, useAnd, autoAnalyze, sources })
      );
    } catch (_) {
      // ignore storage errors
    }
  }, [autoAnalyze, configReady, keywordText, sources, storageKey, useAnd]);

  return {
    keywordText,
    useAnd,
    autoAnalyze,
    sources,
    setKeywordText,
    setUseAnd,
    setAutoAnalyze,
    updateSource,
  };
}
