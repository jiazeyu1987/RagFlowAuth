import { useCallback, useEffect, useMemo, useState } from 'react';
import trainingComplianceApi from './api';
import {
  addYearsToTimestamp,
  buildUserLabel,
  parseDateTimeLocal,
  toDateTimeLocalValue,
  USER_SEARCH_LIMIT,
} from './helpers';
import useTrainingCompliancePrefill from './useTrainingCompliancePrefill';
import useTrainingComplianceUserSearch from './useTrainingComplianceUserSearch';
import { usersApi } from '../users/api';

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

  const clearRecordSelectedUser = useCallback(() => {
    setRecordForm((previous) => ({ ...previous, user_id: '' }));
  }, []);

  const clearCertificationSelectedUser = useCallback(() => {
    setCertificationForm((previous) => ({ ...previous, user_id: '' }));
  }, []);

  const runUserSearch = useCallback(
    async (keyword) => {
      const items = await usersApi.search(keyword, USER_SEARCH_LIMIT);
      mergeUsersIntoDirectory(items);
      return items;
    },
    [mergeUsersIntoDirectory]
  );

  const {
    searchState: recordUserSearch,
    setSearchState: setRecordUserSearch,
    handleKeywordChange: handleRecordUserKeywordChange,
    openSearch: openRecordUserSearch,
    closeSearch: closeRecordUserSearch,
    applySelectedUser: applyRecordUserSearchSelection,
  } = useTrainingComplianceUserSearch({
    buildUserLabel,
    errorMessage: text.userSearchError,
    mapErrorMessage,
    onClearSelection: clearRecordSelectedUser,
    runUserSearch,
  });

  const {
    searchState: certificationUserSearch,
    setSearchState: setCertificationUserSearch,
    handleKeywordChange: handleCertificationUserKeywordChange,
    openSearch: openCertificationUserSearch,
    closeSearch: closeCertificationUserSearch,
    applySelectedUser: applyCertificationUserSearchSelection,
  } = useTrainingComplianceUserSearch({
    buildUserLabel,
    errorMessage: text.userSearchError,
    mapErrorMessage,
    onClearSelection: clearCertificationSelectedUser,
    runUserSearch,
  });

  const applySelectedUserToForms = useCallback(
    (selectedUser) => {
      const nextUserId = String(selectedUser?.user_id || '');
      mergeUsersIntoDirectory([selectedUser]);
      setRecordForm((previous) => ({ ...previous, user_id: nextUserId }));
      setCertificationForm((previous) => ({ ...previous, user_id: nextUserId }));
      applyRecordUserSearchSelection(selectedUser);
      applyCertificationUserSearchSelection(selectedUser);
    },
    [
      applyCertificationUserSearchSelection,
      applyRecordUserSearchSelection,
      mergeUsersIntoDirectory,
    ]
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

      setRequirements(requirementsResponse);
      setRecords(recordsResponse);
      setCertifications(certificationsResponse);
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

  useTrainingCompliancePrefill({
    loading,
    searchParams,
    requirements,
    userDirectory,
    runUserSearch,
    mapErrorMessage,
    userSearchError: text.userSearchError,
    setError,
    setActiveTab,
    applyRecordRequirementCode,
    setCertificationForm,
    applySelectedUserToForms,
  });

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
    openRecordUserSearch,
    closeRecordUserSearch,
    openCertificationUserSearch,
    closeCertificationUserSearch,
    handleRecordUserKeywordChange,
    handleCertificationUserKeywordChange,
    handleSelectRecordUser,
    handleSelectCertificationUser,
    buildDisplayUserLabel,
    handleCreateRecord,
    handleCreateCertification,
  };
}
