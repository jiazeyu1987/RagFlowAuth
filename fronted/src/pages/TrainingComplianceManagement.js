import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import authClient from '../api/authClient';
import trainingComplianceApi from '../features/trainingCompliance/api';
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
  document_review: '文档审批',
  restore_drill_execute: '恢复演练执行',
  knowledge_file_upload: '文件上传',
  knowledge_file_delete: '文件删除',
  knowledge_base_create: '知识库新建',
  knowledge_base_delete: '知识库删除',
};

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
  if (fullName && username && fullName !== username) {
    return `${fullName} (${username})`;
  }
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
                  <div style={{ color: '#6b7280', fontSize: '0.8rem', marginTop: '2px' }}>{item.user_id}</div>
                </button>
              ))
              : null}
          </div>
        ) : null}
      </div>
      <div data-testid={`${testIdPrefix}-selected`} style={{ color: '#6b7280', fontSize: '0.85rem' }}>
        {selectedUser ? `${TEXT.selectedUser}: ${buildUserLabel(selectedUser)} / ${selectedUser.user_id}` : `${TEXT.selectedUser}: ${TEXT.noSelectedUser}`}
      </div>
      <div style={{ color: '#9ca3af', fontSize: '0.8rem' }}>{TEXT.userSearchHint}</div>
    </label>
  );
}

export default function TrainingComplianceManagement() {
  const { user } = useAuth();
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
}
