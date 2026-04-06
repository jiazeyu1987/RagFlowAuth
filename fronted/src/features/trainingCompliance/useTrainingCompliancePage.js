import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import trainingComplianceApi from './api';
import { usersApi } from '../users/api';

const USER_SEARCH_LIMIT = 20;
const USER_SEARCH_DELAY_MS = 250;
const VALID_TABS = new Set(['records', 'certifications']);

const createUserSearchState = () => ({
  keyword: '',
  results: [],
  loading: false,
  open: false,
  error: '',
});

const normalizeUsersResponse = (response) => {
  if (Array.isArray(response)) return response;
  if (Array.isArray(response?.items)) return response.items;
  return [];
};

const toDateTimeLocalValue = (value) => {
  const date = value ? new Date(Number(value)) : new Date();
  if (Number.isNaN(date.getTime())) return '';
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
};

const parseDateTimeLocal = (value) => {
  const text = String(value || '').trim();
  if (!text) return null;
  const timestamp = new Date(text).getTime();
  return Number.isFinite(timestamp) ? timestamp : null;
};

const addYearsToTimestamp = (value, years) => {
  const base = new Date(Number(value));
  if (Number.isNaN(base.getTime())) return Number(value);
  base.setFullYear(base.getFullYear() + years);
  return base.getTime();
};

const buildUserLabel = (user) => {
  if (!user) return '-';
  const fullName = String(user.full_name || '').trim();
  const username = String(user.username || '').trim();
  return fullName || username || String(user.user_id || '-');
};

const resolvePrefillRequirementCode = (requirements, searchParams) => {
  const requestedRequirementCode = String(searchParams.get('requirement_code') || '').trim();
  if (requestedRequirementCode) {
    const matchedRequirement = (requirements || []).find(
      (item) => String(item?.requirement_code || '') === requestedRequirementCode
    );
    if (matchedRequirement) {
      return requestedRequirementCode;
    }
  }

  const requestedControlledAction = String(searchParams.get('controlled_action') || '').trim();
  if (!requestedControlledAction) {
    return '';
  }
  const matchedRequirement = (requirements || []).find(
    (item) => String(item?.controlled_action || '') === requestedControlledAction
  );
  return String(matchedRequirement?.requirement_code || '');
};

export default function useTrainingCompliancePage({
  user,
  searchParams,
  buildDefaultTrainingSummary,
  mapErrorMessage,
  text,
}) {
  const nowMs = Date.now();
  const [loading, setLoading] = useState(true);
  const [savingRecord, setSavingRecord] = useState(false);
  const [savingCertification, setSavingCertification] = useState(false);
  const [activeTab, setActiveTab] = useState('records');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [requirements, setRequirements] = useState([]);
  const [records, setRecords] = useState([]);
  const [certifications, setCertifications] = useState([]);
  const [userDirectory, setUserDirectory] = useState(() =>
    user?.user_id ? { [String(user.user_id)]: user } : {}
  );
  const prefillKeyRef = useRef('');
  const [recordUserSearch, setRecordUserSearch] = useState(createUserSearchState);
  const [certificationUserSearch, setCertificationUserSearch] =
    useState(createUserSearchState);
  const [recordForm, setRecordForm] = useState({
    user_id: '',
    requirement_code: '',
    completed_at: toDateTimeLocalValue(nowMs),
    training_outcome: 'passed',
    effectiveness_status: 'effective',
    effectiveness_summary: buildDefaultTrainingSummary(null),
    training_notes: '',
  });
  const [certificationForm, setCertificationForm] = useState({
    user_id: '',
    requirement_code: '',
    certification_status: 'active',
    valid_until: toDateTimeLocalValue(addYearsToTimestamp(nowMs, 1)),
    certification_notes: '',
  });

  const requirementMap = useMemo(() => {
    const map = new Map();
    (requirements || []).forEach((item) => {
      map.set(String(item.requirement_code || ''), item);
    });
    return map;
  }, [requirements]);

  const recordSelectedUser = recordForm.user_id
    ? userDirectory[String(recordForm.user_id || '')]
    : null;
  const certificationSelectedUser = certificationForm.user_id
    ? userDirectory[String(certificationForm.user_id || '')]
    : null;

  const mergeUsersIntoDirectory = useCallback((items) => {
    setUserDirectory((previous) => {
      let changed = false;
      const next = { ...previous };
      (items || []).forEach((item) => {
        const userId = String(item?.user_id || '').trim();
        if (!userId) return;
        if (next[userId] === item) return;
        next[userId] = item;
        changed = true;
      });
      return changed ? next : previous;
    });
  }, []);

  const applyRecordRequirementCode = useCallback(
    (nextRequirementCode) => {
      setRecordForm((previous) => {
        const currentRequirement = requirementMap.get(String(previous.requirement_code || ''));
        const nextRequirement = requirementMap.get(String(nextRequirementCode || ''));
        const currentDefaultSummary = buildDefaultTrainingSummary(currentRequirement);
        const currentSummary = String(previous.effectiveness_summary || '').trim();
        const shouldReplaceSummary = !currentSummary || currentSummary === currentDefaultSummary;

        return {
          ...previous,
          requirement_code: String(nextRequirementCode || ''),
          effectiveness_summary: shouldReplaceSummary
            ? buildDefaultTrainingSummary(nextRequirement)
            : previous.effectiveness_summary,
        };
      });
    },
    [buildDefaultTrainingSummary, requirementMap]
  );

  const applySelectedUserToForms = useCallback(
    (selectedUser) => {
      const nextUserId = String(selectedUser?.user_id || '');
      const nextLabel = buildUserLabel(selectedUser);
      mergeUsersIntoDirectory([selectedUser]);
      setRecordForm((previous) => ({ ...previous, user_id: nextUserId }));
      setCertificationForm((previous) => ({ ...previous, user_id: nextUserId }));
      setRecordUserSearch((previous) => ({
        ...previous,
        keyword: nextLabel,
        open: false,
        loading: false,
        results: [],
        error: '',
      }));
      setCertificationUserSearch((previous) => ({
        ...previous,
        keyword: nextLabel,
        open: false,
        loading: false,
        results: [],
        error: '',
      }));
    },
    [mergeUsersIntoDirectory]
  );

  useEffect(() => {
    if (user?.user_id) {
      mergeUsersIntoDirectory([user]);
    }
  }, [mergeUsersIntoDirectory, user]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [requirementsResponse, recordsResponse, certificationsResponse] =
        await Promise.all([
          trainingComplianceApi.listRequirements({ limit: 100 }),
          trainingComplianceApi.listRecords({ limit: 100 }),
          trainingComplianceApi.listCertifications({ limit: 100 }),
        ]);

      setRequirements(
        Array.isArray(requirementsResponse?.items) ? requirementsResponse.items : []
      );
      setRecords(Array.isArray(recordsResponse?.items) ? recordsResponse.items : []);
      setCertifications(
        Array.isArray(certificationsResponse?.items) ? certificationsResponse.items : []
      );
    } catch (requestError) {
      setError(mapErrorMessage(requestError?.message, text.loadError));
    } finally {
      setLoading(false);
    }
  }, [mapErrorMessage, text.loadError]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const defaultRequirementCode = String(requirements?.[0]?.requirement_code || '');
    const resolveRequirement = (requirementCode) =>
      requirements.find(
        (item) => String(item?.requirement_code || '') === String(requirementCode || '')
      ) || null;

    setRecordForm((previous) => ({
      ...previous,
      requirement_code: previous.requirement_code || defaultRequirementCode,
      effectiveness_summary: (() => {
        const nextRequirementCode = previous.requirement_code || defaultRequirementCode;
        const currentRequirement = resolveRequirement(previous.requirement_code);
        const nextRequirement = resolveRequirement(nextRequirementCode);
        const currentDefaultSummary = buildDefaultTrainingSummary(currentRequirement);
        const currentSummary = String(previous.effectiveness_summary || '').trim();
        if (!currentSummary || currentSummary === currentDefaultSummary) {
          return buildDefaultTrainingSummary(nextRequirement);
        }
        return previous.effectiveness_summary;
      })(),
    }));

    setCertificationForm((previous) => ({
      ...previous,
      requirement_code: previous.requirement_code || defaultRequirementCode,
      valid_until:
        previous.valid_until ||
        toDateTimeLocalValue(addYearsToTimestamp(Date.now(), 1)),
    }));
  }, [buildDefaultTrainingSummary, requirements]);

  const runUserSearch = useCallback(
    async (keyword) => {
      const items = normalizeUsersResponse(await usersApi.search(keyword, USER_SEARCH_LIMIT));
      mergeUsersIntoDirectory(items);
      return items;
    },
    [mergeUsersIntoDirectory]
  );

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
          setError(mapErrorMessage(requestError?.message, text.userSearchError));
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
    text.userSearchError,
    userDirectory,
  ]);

  useEffect(() => {
    const keyword = String(recordUserSearch.keyword || '').trim();
    if (!recordUserSearch.open) return undefined;
    if (!keyword) {
      setRecordUserSearch((previous) => ({
        ...previous,
        loading: false,
        results: [],
        error: '',
      }));
      return undefined;
    }

    let cancelled = false;
    const timerId = window.setTimeout(async () => {
      setRecordUserSearch((previous) =>
        String(previous.keyword || '').trim() === keyword
          ? { ...previous, loading: true, error: '' }
          : previous
      );
      try {
        const items = await runUserSearch(keyword);
        if (cancelled) return;
        setRecordUserSearch((previous) =>
          String(previous.keyword || '').trim() === keyword && previous.open
            ? { ...previous, loading: false, results: items, error: '' }
            : previous
        );
      } catch (requestError) {
        if (cancelled) return;
        setRecordUserSearch((previous) =>
          String(previous.keyword || '').trim() === keyword && previous.open
            ? {
                ...previous,
                loading: false,
                results: [],
                error: mapErrorMessage(requestError?.message, text.userSearchError),
              }
            : previous
        );
      }
    }, USER_SEARCH_DELAY_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [
    mapErrorMessage,
    recordUserSearch.keyword,
    recordUserSearch.open,
    runUserSearch,
    text.userSearchError,
  ]);

  useEffect(() => {
    const keyword = String(certificationUserSearch.keyword || '').trim();
    if (!certificationUserSearch.open) return undefined;
    if (!keyword) {
      setCertificationUserSearch((previous) => ({
        ...previous,
        loading: false,
        results: [],
        error: '',
      }));
      return undefined;
    }

    let cancelled = false;
    const timerId = window.setTimeout(async () => {
      setCertificationUserSearch((previous) =>
        String(previous.keyword || '').trim() === keyword
          ? { ...previous, loading: true, error: '' }
          : previous
      );
      try {
        const items = await runUserSearch(keyword);
        if (cancelled) return;
        setCertificationUserSearch((previous) =>
          String(previous.keyword || '').trim() === keyword && previous.open
            ? { ...previous, loading: false, results: items, error: '' }
            : previous
        );
      } catch (requestError) {
        if (cancelled) return;
        setCertificationUserSearch((previous) =>
          String(previous.keyword || '').trim() === keyword && previous.open
            ? {
                ...previous,
                loading: false,
                results: [],
                error: mapErrorMessage(requestError?.message, text.userSearchError),
              }
            : previous
        );
      }
    }, USER_SEARCH_DELAY_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [
    certificationUserSearch.keyword,
    certificationUserSearch.open,
    mapErrorMessage,
    runUserSearch,
    text.userSearchError,
  ]);

  const handleRecordUserKeywordChange = useCallback((value) => {
    setRecordForm((previous) => ({ ...previous, user_id: '' }));
    setRecordUserSearch((previous) => ({
      ...previous,
      keyword: value,
      open: true,
      error: '',
      ...(String(value || '').trim() ? {} : { results: [] }),
    }));
  }, []);

  const handleCertificationUserKeywordChange = useCallback((value) => {
    setCertificationForm((previous) => ({ ...previous, user_id: '' }));
    setCertificationUserSearch((previous) => ({
      ...previous,
      keyword: value,
      open: true,
      error: '',
      ...(String(value || '').trim() ? {} : { results: [] }),
    }));
  }, []);

  const buildDisplayUserLabel = useCallback(
    (userId) => {
      const cachedUser = userDirectory[String(userId || '')];
      if (cachedUser) return buildUserLabel(cachedUser);
      return String(userId || '-');
    },
    [userDirectory]
  );

  const handleCreateRecord = useCallback(async () => {
    const selectedRequirement = requirementMap.get(String(recordForm.requirement_code || ''));
    if (!selectedRequirement) {
      setError(mapErrorMessage('requirement_code_required'));
      return;
    }
    if (!String(recordForm.user_id || '').trim()) {
      setError(mapErrorMessage('user_id_required'));
      return;
    }

    const completedAtMs = parseDateTimeLocal(recordForm.completed_at) || Date.now();
    const effectivenessPending = recordForm.effectiveness_status === 'pending_review';

    setSavingRecord(true);
    setError('');
    setSuccess('');
    try {
      await trainingComplianceApi.createRecord({
        requirement_code: String(selectedRequirement.requirement_code || ''),
        user_id: String(recordForm.user_id || ''),
        curriculum_version: String(selectedRequirement.curriculum_version || ''),
        trainer_user_id: String(user?.user_id || ''),
        training_outcome: recordForm.training_outcome,
        effectiveness_status: recordForm.effectiveness_status,
        effectiveness_score:
          recordForm.effectiveness_status === 'effective'
            ? 100
            : recordForm.effectiveness_status === 'ineffective'
              ? 0
              : null,
        effectiveness_summary: String(recordForm.effectiveness_summary || '').trim(),
        training_notes: String(recordForm.training_notes || '').trim() || null,
        completed_at_ms: completedAtMs,
        effectiveness_reviewed_by_user_id: effectivenessPending
          ? null
          : String(user?.user_id || ''),
        effectiveness_reviewed_at_ms: effectivenessPending ? null : completedAtMs,
      });
      setSuccess(text.saveRecordSuccess);
      await loadData();
      setRecordForm((previous) => ({
        ...previous,
        effectiveness_summary: buildDefaultTrainingSummary(selectedRequirement),
        training_notes: '',
        completed_at: toDateTimeLocalValue(Date.now()),
      }));
    } catch (requestError) {
      setError(mapErrorMessage(requestError?.message, text.saveRecordError));
    } finally {
      setSavingRecord(false);
    }
  }, [
    buildDefaultTrainingSummary,
    loadData,
    mapErrorMessage,
    recordForm,
    requirementMap,
    text.saveRecordError,
    text.saveRecordSuccess,
    user?.user_id,
  ]);

  const handleCreateCertification = useCallback(async () => {
    const selectedRequirement = requirementMap.get(
      String(certificationForm.requirement_code || '')
    );
    if (!selectedRequirement) {
      setError(mapErrorMessage('requirement_code_required'));
      return;
    }
    if (!String(certificationForm.user_id || '').trim()) {
      setError(mapErrorMessage('user_id_required'));
      return;
    }

    setSavingCertification(true);
    setError('');
    setSuccess('');
    try {
      await trainingComplianceApi.createCertification({
        requirement_code: String(selectedRequirement.requirement_code || ''),
        user_id: String(certificationForm.user_id || ''),
        granted_by_user_id: String(user?.user_id || ''),
        certification_status: certificationForm.certification_status,
        valid_until_ms: parseDateTimeLocal(certificationForm.valid_until),
        certification_notes:
          String(certificationForm.certification_notes || '').trim() || null,
      });
      setSuccess(text.saveCertificationSuccess);
      await loadData();
      setCertificationForm((previous) => ({
        ...previous,
        certification_notes: '',
        valid_until: toDateTimeLocalValue(addYearsToTimestamp(Date.now(), 1)),
      }));
    } catch (requestError) {
      setError(mapErrorMessage(requestError?.message, text.saveCertificationError));
    } finally {
      setSavingCertification(false);
    }
  }, [
    certificationForm,
    loadData,
    mapErrorMessage,
    requirementMap,
    text.saveCertificationError,
    text.saveCertificationSuccess,
    user?.user_id,
  ]);

  const handleSelectRecordUser = useCallback(
    (selectedUser) => {
      applySelectedUserToForms(selectedUser);
    },
    [applySelectedUserToForms]
  );

  const handleSelectCertificationUser = useCallback(
    (selectedUser) => {
      applySelectedUserToForms(selectedUser);
    },
    [applySelectedUserToForms]
  );

  return {
    loading,
    savingRecord,
    savingCertification,
    activeTab,
    error,
    success,
    requirements,
    records,
    certifications,
    recordSelectedUser,
    certificationSelectedUser,
    recordUserSearch,
    certificationUserSearch,
    recordForm,
    certificationForm,
    setActiveTab,
    setRecordUserSearch,
    setCertificationUserSearch,
    setRecordForm,
    setCertificationForm,
    loadData,
    applyRecordRequirementCode,
    handleRecordUserKeywordChange,
    handleCertificationUserKeywordChange,
    handleSelectRecordUser,
    handleSelectCertificationUser,
    buildDisplayUserLabel,
    handleCreateRecord,
    handleCreateCertification,
  };
}
