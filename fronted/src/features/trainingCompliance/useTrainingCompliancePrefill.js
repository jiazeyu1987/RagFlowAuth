import { useEffect, useRef } from 'react';
import { resolvePrefillRequirementCode, VALID_TABS } from './helpers';

export default function useTrainingCompliancePrefill({
  loading,
  searchParams,
  requirements,
  userDirectory,
  runUserSearch,
  mapErrorMessage,
  userSearchError,
  setError,
  setActiveTab,
  applyRecordRequirementCode,
  setCertificationForm,
  applySelectedUserToForms,
}) {
  const prefillKeyRef = useRef('');

  useEffect(() => {
    if (loading) return undefined;

    const prefillKey = searchParams.toString();
    if (!prefillKey || prefillKeyRef.current === prefillKey) {
      return undefined;
    }

    let cancelled = false;
    const requestedTab = String(searchParams.get('tab') || '').trim();
    const requestedUserId = String(searchParams.get('user_id') || '').trim();
    const nextRequirementCode = resolvePrefillRequirementCode(requirements, searchParams);

    const applyPrefill = async () => {
      if (requestedTab && VALID_TABS.has(requestedTab)) {
        setActiveTab(requestedTab);
      }
      if (nextRequirementCode) {
        applyRecordRequirementCode(nextRequirementCode);
        setCertificationForm((previous) => ({
          ...previous,
          requirement_code: nextRequirementCode,
        }));
      }
      if (!requestedUserId) {
        if (!cancelled) {
          prefillKeyRef.current = prefillKey;
        }
        return;
      }

      try {
        const cachedUser = userDirectory[requestedUserId];
        const items = cachedUser ? [cachedUser] : await runUserSearch(requestedUserId);
        if (cancelled) return;
        const matchedUser =
          items.find((item) => String(item?.user_id || '') === requestedUserId) ||
          items.find((item) => String(item?.username || '') === requestedUserId) ||
          null;
        if (!matchedUser) {
          setError(mapErrorMessage('user_id_not_found'));
        } else {
          applySelectedUserToForms(matchedUser);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(mapErrorMessage(requestError?.message, userSearchError));
        }
      } finally {
        if (!cancelled) {
          prefillKeyRef.current = prefillKey;
        }
      }
    };

    applyPrefill();
    return () => {
      cancelled = true;
    };
  }, [
    applyRecordRequirementCode,
    applySelectedUserToForms,
    loading,
    mapErrorMessage,
    requirements,
    runUserSearch,
    searchParams,
    setActiveTab,
    setCertificationForm,
    setError,
    userDirectory,
    userSearchError,
  ]);
}
