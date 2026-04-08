import { useCallback, useEffect, useState } from 'react';
import { USER_SEARCH_DELAY_MS, createUserSearchState } from './helpers';

export default function useTrainingComplianceUserSearch({
  buildUserLabel,
  errorMessage,
  mapErrorMessage,
  onClearSelection,
  runUserSearch,
}) {
  const [searchState, setSearchState] = useState(createUserSearchState);

  useEffect(() => {
    const keyword = String(searchState.keyword || '').trim();
    if (!searchState.open) return undefined;
    if (!keyword) {
      setSearchState((previous) => ({
        ...previous,
        loading: false,
        results: [],
        error: '',
      }));
      return undefined;
    }

    let cancelled = false;
    const timerId = window.setTimeout(async () => {
      setSearchState((previous) =>
        String(previous.keyword || '').trim() === keyword
          ? { ...previous, loading: true, error: '' }
          : previous
      );
      try {
        const items = await runUserSearch(keyword);
        if (cancelled) return;
        setSearchState((previous) =>
          String(previous.keyword || '').trim() === keyword && previous.open
            ? { ...previous, loading: false, results: items, error: '' }
            : previous
        );
      } catch (requestError) {
        if (cancelled) return;
        setSearchState((previous) =>
          String(previous.keyword || '').trim() === keyword && previous.open
            ? {
                ...previous,
                loading: false,
                results: [],
                error: mapErrorMessage(requestError?.message, errorMessage),
              }
            : previous
        );
      }
    }, USER_SEARCH_DELAY_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [errorMessage, mapErrorMessage, runUserSearch, searchState.keyword, searchState.open]);

  const handleKeywordChange = useCallback(
    (value) => {
      onClearSelection();
      setSearchState((previous) => ({
        ...previous,
        keyword: value,
        open: true,
        error: '',
        ...(String(value || '').trim() ? {} : { results: [] }),
      }));
    },
    [onClearSelection]
  );

  const openSearch = useCallback(() => {
    setSearchState((previous) => ({ ...previous, open: true }));
  }, []);

  const closeSearch = useCallback(() => {
    setSearchState((previous) => ({ ...previous, open: false }));
  }, []);

  const applySelectedUser = useCallback(
    (selectedUser) => {
      const nextLabel = buildUserLabel(selectedUser);
      setSearchState((previous) => ({
        ...previous,
        keyword: nextLabel,
        open: false,
        loading: false,
        results: [],
        error: '',
      }));
    },
    [buildUserLabel]
  );

  return {
    searchState,
    setSearchState,
    handleKeywordChange,
    openSearch,
    closeSearch,
    applySelectedUser,
  };
}
