import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import trainingComplianceApi from '../features/trainingCompliance/api';
import { usersApi } from '../features/users/api';
import { useAuth } from '../hooks/useAuth';

const USER_SEARCH_LIMIT = 20;
const USER_SEARCH_DELAY_MS = 250;

const cardStyle = {
  background: 'white',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '16px',
  marginTop: '16px',
};

const tableStyle = {
  width: '100%',
  borderCollapse: 'collapse',
};

const cellStyle = {
  borderBottom: '1px solid #e5e7eb',
  textAlign: 'left',
  padding: '8px',
  verticalAlign: 'top',
  fontSize: '0.9rem',
};

const inputStyle = {
  padding: '8px 10px',
  borderRadius: '8px',
  border: '1px solid #d1d5db',
  width: '100%',
  background: '#ffffff',
};

const buttonStyle = {
  border: '1px solid #d1d5db',
  borderRadius: '8px',
  background: '#ffffff',
  color: '#111827',
  cursor: 'pointer',
  padding: '8px 12px',
};

const primaryButtonStyle = {
  ...buttonStyle,
  border: 'none',
  background: '#2563eb',
  color: '#ffffff',
};

const TEXT = {
  loading: '正在加载培训合规数据...',
  title: '培训合规管理',
  subtitle: '仅管理员可录入和维护培训记录与上岗认证。请先录入培训记录，再录入上岗认证。',
  refresh: '刷新',
  loadError: '加载培训合规数据失败',
  defaultError: '操作失败',
  userSearchError: '用户搜索失败',
  requirementSection: '培训要求',
  requirementCode: '要求编码',
  controlledAction: '受控动作',
  roleCode: '适用角色',
  curriculumVersion: '课程版本',
  recertificationInterval: '复训周期（天）',
  active: '启用',
  noRequirements: '暂无培训要求',
  yes: '是',
  no: '否',
  recordsTab: '培训记录',
  certificationsTab: '上岗认证',
  recordSection: '录入培训记录',
  certificationSection: '录入上岗认证',
  targetUser: '目标用户',
  userSearchPlaceholder: '输入姓名、账号或用户 ID 模糊查询',
  userSearchHint: '先输入关键词，再从下拉结果中选择用户',
  userSearchLoading: '正在搜索用户...',
  userSearchEmpty: '未找到匹配用户',
  selectedUser: '已选择用户',
  trainingRequirement: '培训要求',
  completedAt: '完成时间',
  trainingOutcome: '培训结果',
  effectivenessStatus: '有效性评估',
  effectivenessSummary: '培训总结',
  notes: '备注',
  certificationStatus: '认证状态',
  validUntil: '有效期截止',
  saveRecord: '保存培训记录',
  saveRecordPending: '保存中...',
  saveCertification: '保存上岗认证',
  saveCertificationPending: '保存中...',
  saveRecordSuccess: '培训记录已保存。',
  saveCertificationSuccess: '上岗认证已保存。',
  saveRecordError: '保存培训记录失败',
  saveCertificationError: '保存上岗认证失败',
  latestRecords: '最新培训记录',
  latestCertifications: '最新上岗认证',
  noRecords: '暂无培训记录',
  noCertifications: '暂无上岗认证',
  grantedAt: '授予时间',
  noSelectedUser: '未选择用户',
};

const TRAINING_OUTCOME_OPTIONS = [
  { value: 'passed', label: '通过' },
  { value: 'failed', label: '未通过' },
];

const EFFECTIVENESS_OPTIONS = [
  { value: 'effective', label: '有效' },
  { value: 'ineffective', label: '无效' },
  { value: 'pending_review', label: '待评估' },
];

const CERTIFICATION_STATUS_OPTIONS = [
  { value: 'active', label: '有效' },
  { value: 'suspended', label: '暂停' },
  { value: 'revoked', label: '撤销' },
  { value: 'expired', label: '过期' },
];

const TRAINING_OUTCOME_LABELS = {
  passed: '通过',
  failed: '未通过',
};

const EFFECTIVENESS_LABELS = {
  effective: '有效',
  ineffective: '无效',
  pending_review: '待评估',
};

const CERTIFICATION_STATUS_LABELS = {
  active: '有效',
  suspended: '暂停',
  revoked: '撤销',
  expired: '过期',
};

const CONTROLLED_ACTION_LABELS = {
  document_review: '审批决策',
  restore_drill_execute: '恢复演练执行',
  knowledge_file_upload: '文件上传',
  knowledge_file_delete: '文件删除',
  knowledge_base_create: '知识库新建',
  knowledge_base_delete: '知识库删除',
};

const VALID_TABS = new Set(['records', 'certifications']);

const ERROR_MESSAGES = {
  requirement_code_required: '请选择培训要求。',
  user_id_required: '请选择目标用户。',
  trainer_user_id_required: '当前管理员账号缺少培训讲师信息。',
  granted_by_user_id_required: '当前管理员账号缺少认证授予人信息。',
  effectiveness_summary_required: '请填写培训总结。',
  user_id_not_found: '目标用户不存在，请刷新页面后重试。',
  trainer_user_id_not_found: '培训讲师不存在，请检查当前管理员账号。',
  granted_by_user_id_not_found: '认证授予人不存在，请检查当前管理员账号。',
  training_requirement_not_found: '培训要求不存在，请刷新页面后重试。',
  training_record_missing: '请先录入培训记录，再录入上岗认证。',
  training_curriculum_outdated: '该用户现有培训版本已过期，请先补录最新版本培训记录。',
  training_outcome_not_passed: '该用户培训未通过，不能直接授予上岗认证。',
  training_effectiveness_not_met: '该用户培训有效性评估未通过，不能直接授予上岗认证。',
  invalid_training_outcome: '培训结果无效。',
  invalid_effectiveness_status: '有效性评估状态无效。',
  invalid_certification_status: '认证状态无效。',
  invalid_valid_until_ms: '认证有效期无效，请检查日期。',
};

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

const formatTime = (value) => {
  const ms = Number(value || 0);
  if (!Number.isFinite(ms) || ms <= 0) return '-';
  return new Date(ms).toLocaleString();
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

const mapErrorMessage = (message, fallback) => {
  const code = String(message || '').trim();
  if (!code) return fallback || TEXT.defaultError;
  return ERROR_MESSAGES[code] || code || fallback || TEXT.defaultError;
};

const buildUserLabel = (user) => {
  if (!user) return '-';
  const fullName = String(user.full_name || '').trim();
  const username = String(user.username || '').trim();
  return fullName || username || String(user.user_id || '-');
};

const getTrainingOutcomeLabel = (value) =>
  TRAINING_OUTCOME_LABELS[String(value || '')] || String(value || '-');

const getEffectivenessLabel = (value) =>
  EFFECTIVENESS_LABELS[String(value || '')] || String(value || '-');

const getCertificationStatusLabel = (value) =>
  CERTIFICATION_STATUS_LABELS[String(value || '')] || String(value || '-');

const getControlledActionLabel = (value) =>
  CONTROLLED_ACTION_LABELS[String(value || '')] || String(value || '-');

const buildRequirementOptionLabel = (requirement) => {
  if (!requirement) return '-';
  return `${requirement.requirement_code} | ${getControlledActionLabel(requirement.controlled_action)} | ${requirement.curriculum_version}`;
};

const buildDefaultTrainingSummary = (requirement) => {
  const requirementName = String(requirement?.requirement_name || '').trim();
  const actionLabel = getControlledActionLabel(requirement?.controlled_action || '');
  if (requirementName) {
    return `已完成《${requirementName}》培训，满足${actionLabel}上岗要求。`;
  }
  if (actionLabel && actionLabel !== '-') {
    return `已完成${actionLabel}相关培训并通过考核。`;
  }
  return '已完成培训并通过考核。';
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

function UserLookupField({
  label,
  placeholder,
  selectedUser,
  searchState,
  onInputChange,
  onFocus,
  onBlur,
  onSelectUser,
  testIdPrefix,
}) {
  const blurTimerRef = useRef(null);

  useEffect(() => () => {
    if (blurTimerRef.current) {
      window.clearTimeout(blurTimerRef.current);
    }
  }, []);

  const handleBlur = () => {
    if (blurTimerRef.current) {
      window.clearTimeout(blurTimerRef.current);
    }
    blurTimerRef.current = window.setTimeout(() => {
      onBlur();
    }, 120);
  };

  const handleFocus = () => {
    if (blurTimerRef.current) {
      window.clearTimeout(blurTimerRef.current);
    }
    onFocus();
  };

  const showDropdown = searchState.open && (
    searchState.loading
    || !!searchState.error
    || searchState.results.length > 0
    || String(searchState.keyword || '').trim()
  );

  return (
    <label style={{ display: 'grid', gap: '6px' }}>
      <span>{label}</span>
      <div style={{ position: 'relative' }}>
        <input
          data-testid={`${testIdPrefix}-input`}
          value={searchState.keyword}
          onChange={(event) => onInputChange(event.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={placeholder}
          autoComplete="off"
          style={inputStyle}
        />
        {showDropdown ? (
          <div
            data-testid={`${testIdPrefix}-results`}
            style={{
              position: 'absolute',
              zIndex: 10,
              top: 'calc(100% + 6px)',
              left: 0,
              right: 0,
              background: '#ffffff',
              border: '1px solid #d1d5db',
              borderRadius: '10px',
              boxShadow: '0 12px 30px rgba(15, 23, 42, 0.12)',
              overflow: 'hidden',
            }}
          >
            {searchState.loading ? (
              <div style={{ padding: '10px 12px', color: '#6b7280', fontSize: '0.9rem' }}>{TEXT.userSearchLoading}</div>
            ) : null}
            {!searchState.loading && searchState.error ? (
              <div style={{ padding: '10px 12px', color: '#991b1b', fontSize: '0.9rem' }}>{searchState.error}</div>
            ) : null}
            {!searchState.loading && !searchState.error && searchState.results.length === 0 ? (
              <div style={{ padding: '10px 12px', color: '#6b7280', fontSize: '0.9rem' }}>{TEXT.userSearchEmpty}</div>
            ) : null}
            {!searchState.loading && !searchState.error
              ? searchState.results.map((item) => (
                <button
                  key={item.user_id}
                  type="button"
                  data-testid={`${testIdPrefix}-result-${item.user_id}`}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    onSelectUser(item);
                  }}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    border: 'none',
                    background: '#ffffff',
                    padding: '10px 12px',
                    cursor: 'pointer',
                    borderTop: '1px solid #f3f4f6',
                  }}
                >
                  <div style={{ fontWeight: 600 }}>{buildUserLabel(item)}</div>
                  <div style={{ color: '#6b7280', fontSize: '0.8rem', marginTop: '2px' }}>{item.department_name || item.company_name || ''}</div>
                </button>
              ))
              : null}
          </div>
        ) : null}
      </div>
      <div data-testid={`${testIdPrefix}-selected`} style={{ color: '#6b7280', fontSize: '0.85rem' }}>
        {selectedUser ? `${TEXT.selectedUser}: ${buildUserLabel(selectedUser)}` : `${TEXT.selectedUser}: ${TEXT.noSelectedUser}`}
      </div>
      <div style={{ color: '#9ca3af', fontSize: '0.8rem' }}>{TEXT.userSearchHint}</div>
    </label>
  );
}

export default function TrainingComplianceManagement() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
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
  const [userDirectory, setUserDirectory] = useState(() => (
    user?.user_id ? { [String(user.user_id)]: user } : {}
  ));
  const prefillKeyRef = useRef('');
  const [recordUserSearch, setRecordUserSearch] = useState(createUserSearchState);
  const [certificationUserSearch, setCertificationUserSearch] = useState(createUserSearchState);
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

  const recordSelectedUser = recordForm.user_id ? userDirectory[String(recordForm.user_id || '')] : null;
  const certificationSelectedUser = certificationForm.user_id ? userDirectory[String(certificationForm.user_id || '')] : null;

  const mergeUsersIntoDirectory = useCallback((items) => {
    setUserDirectory((prev) => {
      let changed = false;
      const next = { ...prev };
      (items || []).forEach((item) => {
        const userId = String(item?.user_id || '').trim();
        if (!userId) return;
        if (next[userId] === item) return;
        next[userId] = item;
        changed = true;
      });
      return changed ? next : prev;
    });
  }, []);

  const applyRecordRequirementCode = useCallback((nextRequirementCode) => {
    setRecordForm((prev) => {
      const currentRequirement = requirementMap.get(String(prev.requirement_code || ''));
      const nextRequirement = requirementMap.get(String(nextRequirementCode || ''));
      const currentDefaultSummary = buildDefaultTrainingSummary(currentRequirement);
      const currentSummary = String(prev.effectiveness_summary || '').trim();
      const shouldReplaceSummary = !currentSummary || currentSummary === currentDefaultSummary;
      return {
        ...prev,
        requirement_code: String(nextRequirementCode || ''),
        effectiveness_summary: shouldReplaceSummary
          ? buildDefaultTrainingSummary(nextRequirement)
          : prev.effectiveness_summary,
      };
    });
  }, [requirementMap]);

  const applySelectedUserToForms = useCallback((selectedUser) => {
    const nextUserId = String(selectedUser?.user_id || '');
    const nextLabel = buildUserLabel(selectedUser);
    mergeUsersIntoDirectory([selectedUser]);
    setRecordForm((prev) => ({ ...prev, user_id: nextUserId }));
    setCertificationForm((prev) => ({ ...prev, user_id: nextUserId }));
    setRecordUserSearch((prev) => ({
      ...prev,
      keyword: nextLabel,
      open: false,
      loading: false,
      results: [],
      error: '',
    }));
    setCertificationUserSearch((prev) => ({
      ...prev,
      keyword: nextLabel,
      open: false,
      loading: false,
      results: [],
      error: '',
    }));
  }, [mergeUsersIntoDirectory]);

  useEffect(() => {
    if (user?.user_id) {
      mergeUsersIntoDirectory([user]);
    }
  }, [user, mergeUsersIntoDirectory]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [requirementsResp, recordsResp, certificationsResp] = await Promise.all([
        trainingComplianceApi.listRequirements({ limit: 100 }),
        trainingComplianceApi.listRecords({ limit: 100 }),
        trainingComplianceApi.listCertifications({ limit: 100 }),
      ]);

      const nextRequirements = Array.isArray(requirementsResp?.items) ? requirementsResp.items : [];
      const nextRecords = Array.isArray(recordsResp?.items) ? recordsResp.items : [];
      const nextCertifications = Array.isArray(certificationsResp?.items) ? certificationsResp.items : [];

      setRequirements(nextRequirements);
      setRecords(nextRecords);
      setCertifications(nextCertifications);
    } catch (requestError) {
      setError(mapErrorMessage(requestError?.message, TEXT.loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const defaultRequirementCode = String(requirements?.[0]?.requirement_code || '');
    const resolveRequirement = (requirementCode) =>
      requirements.find((item) => String(item?.requirement_code || '') === String(requirementCode || '')) || null;

    setRecordForm((prev) => ({
      ...prev,
      requirement_code: prev.requirement_code || defaultRequirementCode,
      effectiveness_summary: (() => {
        const nextRequirementCode = prev.requirement_code || defaultRequirementCode;
        const currentRequirement = resolveRequirement(prev.requirement_code);
        const nextRequirement = resolveRequirement(nextRequirementCode);
        const currentDefaultSummary = buildDefaultTrainingSummary(currentRequirement);
        const currentSummary = String(prev.effectiveness_summary || '').trim();
        if (!currentSummary || currentSummary === currentDefaultSummary) {
          return buildDefaultTrainingSummary(nextRequirement);
        }
        return prev.effectiveness_summary;
      })(),
    }));

    setCertificationForm((prev) => ({
      ...prev,
      requirement_code: prev.requirement_code || defaultRequirementCode,
      valid_until: prev.valid_until || toDateTimeLocalValue(addYearsToTimestamp(Date.now(), 1)),
    }));
  }, [requirements]);

  const runUserSearch = useCallback(async (keyword) => {
    const items = normalizeUsersResponse(await usersApi.search(keyword, USER_SEARCH_LIMIT));
    mergeUsersIntoDirectory(items);
    return items;
  }, [mergeUsersIntoDirectory]);

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
        setCertificationForm((prev) => ({ ...prev, requirement_code: nextRequirementCode }));
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
        const matchedUser = items.find((item) => String(item?.user_id || '') === requestedUserId)
          || items.find((item) => String(item?.username || '') === requestedUserId)
          || null;
        if (!matchedUser) {
          setError(mapErrorMessage('user_id_not_found'));
        } else {
          applySelectedUserToForms(matchedUser);
        }
      } catch (requestError) {
        if (!cancelled) {
          setError(mapErrorMessage(requestError?.message, TEXT.userSearchError));
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
    loading,
    searchParams,
    requirements,
    userDirectory,
    applyRecordRequirementCode,
    applySelectedUserToForms,
    runUserSearch,
  ]);

  useEffect(() => {
    const keyword = String(recordUserSearch.keyword || '').trim();
    if (!recordUserSearch.open) return undefined;
    if (!keyword) {
      setRecordUserSearch((prev) => ({ ...prev, loading: false, results: [], error: '' }));
      return undefined;
    }
    let cancelled = false;
    const timerId = window.setTimeout(async () => {
      setRecordUserSearch((prev) => (
        String(prev.keyword || '').trim() === keyword
          ? { ...prev, loading: true, error: '' }
          : prev
      ));
      try {
        const items = await runUserSearch(keyword);
        if (cancelled) return;
        setRecordUserSearch((prev) => (
          String(prev.keyword || '').trim() === keyword && prev.open
            ? { ...prev, loading: false, results: items, error: '' }
            : prev
        ));
      } catch (requestError) {
        if (cancelled) return;
        setRecordUserSearch((prev) => (
          String(prev.keyword || '').trim() === keyword && prev.open
            ? { ...prev, loading: false, results: [], error: mapErrorMessage(requestError?.message, TEXT.userSearchError) }
            : prev
        ));
      }
    }, USER_SEARCH_DELAY_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [recordUserSearch.keyword, recordUserSearch.open, runUserSearch]);

  useEffect(() => {
    const keyword = String(certificationUserSearch.keyword || '').trim();
    if (!certificationUserSearch.open) return undefined;
    if (!keyword) {
      setCertificationUserSearch((prev) => ({ ...prev, loading: false, results: [], error: '' }));
      return undefined;
    }
    let cancelled = false;
    const timerId = window.setTimeout(async () => {
      setCertificationUserSearch((prev) => (
        String(prev.keyword || '').trim() === keyword
          ? { ...prev, loading: true, error: '' }
          : prev
      ));
      try {
        const items = await runUserSearch(keyword);
        if (cancelled) return;
        setCertificationUserSearch((prev) => (
          String(prev.keyword || '').trim() === keyword && prev.open
            ? { ...prev, loading: false, results: items, error: '' }
            : prev
        ));
      } catch (requestError) {
        if (cancelled) return;
        setCertificationUserSearch((prev) => (
          String(prev.keyword || '').trim() === keyword && prev.open
            ? { ...prev, loading: false, results: [], error: mapErrorMessage(requestError?.message, TEXT.userSearchError) }
            : prev
        ));
      }
    }, USER_SEARCH_DELAY_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [certificationUserSearch.keyword, certificationUserSearch.open, runUserSearch]);

  const handleRecordUserKeywordChange = (value) => {
    setRecordForm((prev) => ({ ...prev, user_id: '' }));
    setRecordUserSearch((prev) => ({
      ...prev,
      keyword: value,
      open: true,
      error: '',
      ...(String(value || '').trim() ? {} : { results: [] }),
    }));
  };

  const handleCertificationUserKeywordChange = (value) => {
    setCertificationForm((prev) => ({ ...prev, user_id: '' }));
    setCertificationUserSearch((prev) => ({
      ...prev,
      keyword: value,
      open: true,
      error: '',
      ...(String(value || '').trim() ? {} : { results: [] }),
    }));
  };

  const handleSelectRecordUser = (selectedUser) => {
    applySelectedUserToForms(selectedUser);
  };

  const handleSelectCertificationUser = (selectedUser) => {
    applySelectedUserToForms(selectedUser);
  };

  const buildDisplayUserLabel = (userId) => {
    const cachedUser = userDirectory[String(userId || '')];
    if (cachedUser) return buildUserLabel(cachedUser);
    return String(userId || '-');
  };

  const handleCreateRecord = async () => {
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
            : (recordForm.effectiveness_status === 'ineffective' ? 0 : null),
        effectiveness_summary: String(recordForm.effectiveness_summary || '').trim(),
        training_notes: String(recordForm.training_notes || '').trim() || null,
        completed_at_ms: completedAtMs,
        effectiveness_reviewed_by_user_id: effectivenessPending ? null : String(user?.user_id || ''),
        effectiveness_reviewed_at_ms: effectivenessPending ? null : completedAtMs,
      });
      setSuccess(TEXT.saveRecordSuccess);
      await loadData();
      setRecordForm((prev) => ({
        ...prev,
        effectiveness_summary: buildDefaultTrainingSummary(selectedRequirement),
        training_notes: '',
        completed_at: toDateTimeLocalValue(Date.now()),
      }));
    } catch (requestError) {
      setError(mapErrorMessage(requestError?.message, TEXT.saveRecordError));
    } finally {
      setSavingRecord(false);
    }
  };

  const handleCreateCertification = async () => {
    const selectedRequirement = requirementMap.get(String(certificationForm.requirement_code || ''));
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
        certification_notes: String(certificationForm.certification_notes || '').trim() || null,
      });
      setSuccess(TEXT.saveCertificationSuccess);
      await loadData();
      setCertificationForm((prev) => ({
        ...prev,
        certification_notes: '',
        valid_until: toDateTimeLocalValue(addYearsToTimestamp(Date.now(), 1)),
      }));
    } catch (requestError) {
      setError(mapErrorMessage(requestError?.message, TEXT.saveCertificationError));
    } finally {
      setSavingCertification(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '12px' }}>{TEXT.loading}</div>;
  }

  return (
    <div style={{ maxWidth: '1400px' }} data-testid="training-compliance-page">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', alignItems: 'center', flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ margin: 0 }}>{TEXT.title}</h2>
          <div style={{ color: '#6b7280', marginTop: '6px' }}>{TEXT.subtitle}</div>
        </div>
        <button type="button" onClick={loadData} style={buttonStyle}>
          {TEXT.refresh}
        </button>
      </div>

      {error ? (
        <div
          data-testid="training-compliance-error"
          style={{ marginTop: '12px', padding: '10px 12px', background: '#fef2f2', color: '#991b1b', borderRadius: '10px' }}
        >
          {error}
        </div>
      ) : null}

      {success ? (
        <div
          data-testid="training-compliance-success"
          style={{ marginTop: '12px', padding: '10px 12px', background: '#ecfdf5', color: '#166534', borderRadius: '10px' }}
        >
          {success}
        </div>
      ) : null}

      <div style={cardStyle}>
        <h3 style={{ marginTop: 0 }}>{TEXT.requirementSection}</h3>
        <div style={{ overflowX: 'auto' }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={cellStyle}>{TEXT.requirementCode}</th>
                <th style={cellStyle}>{TEXT.controlledAction}</th>
                <th style={cellStyle}>{TEXT.roleCode}</th>
                <th style={cellStyle}>{TEXT.curriculumVersion}</th>
                <th style={cellStyle}>{TEXT.recertificationInterval}</th>
                <th style={cellStyle}>{TEXT.active}</th>
              </tr>
            </thead>
            <tbody>
              {requirements.length === 0 ? (
                <tr>
                  <td style={cellStyle} colSpan={6}>
                    {TEXT.noRequirements}
                  </td>
                </tr>
              ) : requirements.map((item) => (
                <tr key={item.requirement_code}>
                  <td style={cellStyle}>{item.requirement_code}</td>
                  <td style={cellStyle}>{getControlledActionLabel(item.controlled_action)}</td>
                  <td style={cellStyle}>{item.role_code}</td>
                  <td style={cellStyle}>{item.curriculum_version}</td>
                  <td style={cellStyle}>{item.recertification_interval_days}</td>
                  <td style={cellStyle}>{item.active ? TEXT.yes : TEXT.no}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div style={{ display: 'flex', gap: '8px', marginTop: '16px', flexWrap: 'wrap' }}>
        <button
          type="button"
          data-testid="training-tab-records"
          onClick={() => setActiveTab('records')}
          style={activeTab === 'records' ? primaryButtonStyle : buttonStyle}
        >
          {TEXT.recordsTab}
        </button>
        <button
          type="button"
          data-testid="training-tab-certifications"
          onClick={() => setActiveTab('certifications')}
          style={activeTab === 'certifications' ? primaryButtonStyle : buttonStyle}
        >
          {TEXT.certificationsTab}
        </button>
      </div>

      {activeTab === 'records' ? (
        <>
          <section style={cardStyle} data-testid="training-records-tab-panel">
            <h3 style={{ marginTop: 0 }}>{TEXT.recordSection}</h3>
            <div style={{ display: 'grid', gap: '12px' }}>
              <UserLookupField
                label={TEXT.targetUser}
                placeholder={TEXT.userSearchPlaceholder}
                selectedUser={recordSelectedUser}
                searchState={recordUserSearch}
                onInputChange={handleRecordUserKeywordChange}
                onFocus={() => setRecordUserSearch((prev) => ({ ...prev, open: true }))}
                onBlur={() => setRecordUserSearch((prev) => ({ ...prev, open: false }))}
                onSelectUser={handleSelectRecordUser}
                testIdPrefix="training-record-user-search"
              />
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.trainingRequirement}</span>
                <select
                  data-testid="training-record-requirement"
                  value={recordForm.requirement_code}
                  onChange={(event) => {
                    const nextRequirementCode = event.target.value;
                    setRecordForm((prev) => {
                      const currentRequirement = requirementMap.get(String(prev.requirement_code || ''));
                      const nextRequirement = requirementMap.get(String(nextRequirementCode || ''));
                      const currentDefaultSummary = buildDefaultTrainingSummary(currentRequirement);
                      const currentSummary = String(prev.effectiveness_summary || '').trim();
                      const shouldReplaceSummary = !currentSummary || currentSummary === currentDefaultSummary;
                      return {
                        ...prev,
                        requirement_code: nextRequirementCode,
                        effectiveness_summary: shouldReplaceSummary
                          ? buildDefaultTrainingSummary(nextRequirement)
                          : prev.effectiveness_summary,
                      };
                    });
                  }}
                  style={inputStyle}
                >
                  {requirements.length === 0 ? (
                    <option value="">{TEXT.noRequirements}</option>
                  ) : requirements.map((item) => (
                    <option key={item.requirement_code} value={item.requirement_code}>
                      {buildRequirementOptionLabel(item)}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.completedAt}</span>
                <input
                  data-testid="training-record-completed-at"
                  type="datetime-local"
                  value={recordForm.completed_at}
                  onChange={(event) => setRecordForm((prev) => ({ ...prev, completed_at: event.target.value }))}
                  style={inputStyle}
                />
              </label>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' }}>
                <label style={{ display: 'grid', gap: '6px' }}>
                  <span>{TEXT.trainingOutcome}</span>
                  <select
                    data-testid="training-record-outcome"
                    value={recordForm.training_outcome}
                    onChange={(event) => setRecordForm((prev) => ({ ...prev, training_outcome: event.target.value }))}
                    style={inputStyle}
                  >
                    {TRAINING_OUTCOME_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
                <label style={{ display: 'grid', gap: '6px' }}>
                  <span>{TEXT.effectivenessStatus}</span>
                  <select
                    data-testid="training-record-effectiveness"
                    value={recordForm.effectiveness_status}
                    onChange={(event) => setRecordForm((prev) => ({ ...prev, effectiveness_status: event.target.value }))}
                    style={inputStyle}
                  >
                    {EFFECTIVENESS_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.effectivenessSummary}</span>
                <textarea
                  data-testid="training-record-summary"
                  rows={3}
                  value={recordForm.effectiveness_summary}
                  onChange={(event) => setRecordForm((prev) => ({ ...prev, effectiveness_summary: event.target.value }))}
                  style={{ ...inputStyle, resize: 'vertical' }}
                />
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.notes}</span>
                <textarea
                  data-testid="training-record-notes"
                  rows={3}
                  value={recordForm.training_notes}
                  onChange={(event) => setRecordForm((prev) => ({ ...prev, training_notes: event.target.value }))}
                  style={{ ...inputStyle, resize: 'vertical' }}
                />
              </label>
              <button
                type="button"
                data-testid="training-record-submit"
                onClick={handleCreateRecord}
                disabled={savingRecord}
                style={primaryButtonStyle}
              >
                {savingRecord ? TEXT.saveRecordPending : TEXT.saveRecord}
              </button>
            </div>
          </section>

          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>{TEXT.latestRecords}</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={cellStyle}>{TEXT.targetUser}</th>
                    <th style={cellStyle}>{TEXT.requirementCode}</th>
                    <th style={cellStyle}>{TEXT.curriculumVersion}</th>
                    <th style={cellStyle}>{TEXT.trainingOutcome}</th>
                    <th style={cellStyle}>{TEXT.effectivenessStatus}</th>
                    <th style={cellStyle}>{TEXT.completedAt}</th>
                  </tr>
                </thead>
                <tbody>
                  {records.length === 0 ? (
                    <tr>
                      <td style={cellStyle} colSpan={6}>
                        {TEXT.noRecords}
                      </td>
                    </tr>
                  ) : records.map((item) => (
                    <tr key={item.record_id}>
                      <td style={cellStyle}>{buildDisplayUserLabel(item.user_id)}</td>
                      <td style={cellStyle}>{item.requirement_code}</td>
                      <td style={cellStyle}>{item.curriculum_version}</td>
                      <td style={cellStyle}>{getTrainingOutcomeLabel(item.training_outcome)}</td>
                      <td style={cellStyle}>{getEffectivenessLabel(item.effectiveness_status)}</td>
                      <td style={cellStyle}>{formatTime(item.completed_at_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        <>
          <section style={cardStyle} data-testid="training-certifications-tab-panel">
            <h3 style={{ marginTop: 0 }}>{TEXT.certificationSection}</h3>
            <div style={{ display: 'grid', gap: '12px' }}>
              <UserLookupField
                label={TEXT.targetUser}
                placeholder={TEXT.userSearchPlaceholder}
                selectedUser={certificationSelectedUser}
                searchState={certificationUserSearch}
                onInputChange={handleCertificationUserKeywordChange}
                onFocus={() => setCertificationUserSearch((prev) => ({ ...prev, open: true }))}
                onBlur={() => setCertificationUserSearch((prev) => ({ ...prev, open: false }))}
                onSelectUser={handleSelectCertificationUser}
                testIdPrefix="training-certification-user-search"
              />
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.trainingRequirement}</span>
                <select
                  data-testid="training-certification-requirement"
                  value={certificationForm.requirement_code}
                  onChange={(event) => setCertificationForm((prev) => ({ ...prev, requirement_code: event.target.value }))}
                  style={inputStyle}
                >
                  {requirements.length === 0 ? (
                    <option value="">{TEXT.noRequirements}</option>
                  ) : requirements.map((item) => (
                    <option key={item.requirement_code} value={item.requirement_code}>
                      {buildRequirementOptionLabel(item)}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.certificationStatus}</span>
                <select
                  data-testid="training-certification-status"
                  value={certificationForm.certification_status}
                  onChange={(event) => setCertificationForm((prev) => ({ ...prev, certification_status: event.target.value }))}
                  style={inputStyle}
                >
                  {CERTIFICATION_STATUS_OPTIONS.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.validUntil}</span>
                <input
                  data-testid="training-certification-valid-until"
                  type="datetime-local"
                  value={certificationForm.valid_until}
                  onChange={(event) => setCertificationForm((prev) => ({ ...prev, valid_until: event.target.value }))}
                  style={inputStyle}
                />
              </label>
              <label style={{ display: 'grid', gap: '6px' }}>
                <span>{TEXT.notes}</span>
                <textarea
                  data-testid="training-certification-notes"
                  rows={3}
                  value={certificationForm.certification_notes}
                  onChange={(event) => setCertificationForm((prev) => ({ ...prev, certification_notes: event.target.value }))}
                  style={{ ...inputStyle, resize: 'vertical' }}
                />
              </label>
              <button
                type="button"
                data-testid="training-certification-submit"
                onClick={handleCreateCertification}
                disabled={savingCertification}
                style={primaryButtonStyle}
              >
                {savingCertification ? TEXT.saveCertificationPending : TEXT.saveCertification}
              </button>
            </div>
          </section>

          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>{TEXT.latestCertifications}</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={tableStyle}>
                <thead>
                  <tr>
                    <th style={cellStyle}>{TEXT.targetUser}</th>
                    <th style={cellStyle}>{TEXT.requirementCode}</th>
                    <th style={cellStyle}>{TEXT.curriculumVersion}</th>
                    <th style={cellStyle}>{TEXT.certificationStatus}</th>
                    <th style={cellStyle}>{TEXT.validUntil}</th>
                    <th style={cellStyle}>{TEXT.grantedAt}</th>
                  </tr>
                </thead>
                <tbody>
                  {certifications.length === 0 ? (
                    <tr>
                      <td style={cellStyle} colSpan={6}>
                        {TEXT.noCertifications}
                      </td>
                    </tr>
                  ) : certifications.map((item) => (
                    <tr key={item.certification_id}>
                      <td style={cellStyle}>{buildDisplayUserLabel(item.user_id)}</td>
                      <td style={cellStyle}>{item.requirement_code}</td>
                      <td style={cellStyle}>{item.curriculum_version}</td>
                      <td style={cellStyle}>{getCertificationStatusLabel(item.certification_status)}</td>
                      <td style={cellStyle}>{formatTime(item.valid_until_ms)}</td>
                      <td style={cellStyle}>{formatTime(item.granted_at_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
