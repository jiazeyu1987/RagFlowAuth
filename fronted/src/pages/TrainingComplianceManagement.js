import React, { useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import TrainingCertificationsSection from '../features/trainingCompliance/components/TrainingCertificationsSection';
import TrainingRecordsSection from '../features/trainingCompliance/components/TrainingRecordsSection';
import TrainingRequirementsSection from '../features/trainingCompliance/components/TrainingRequirementsSection';
import {
  bannerErrorStyle,
  bannerSuccessStyle,
  buttonStyle,
  pageContainerStyle,
  pageHeaderStyle,
  primaryButtonStyle,
  tabListStyle,
} from '../features/trainingCompliance/pageStyles';
import useTrainingCompliancePage from '../features/trainingCompliance/useTrainingCompliancePage';
import { useAuth } from '../hooks/useAuth';

const TEXT = {
  loading: '正在加载培训合规数据...',
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

const formatTime = (value) => {
  const ms = Number(value || 0);
  if (!Number.isFinite(ms) || ms <= 0) return '-';
  return new Date(ms).toLocaleString();
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

export default function TrainingComplianceManagement() {
  const { user } = useAuth();
  const [searchParams] = useSearchParams();
  const {
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
  } = useTrainingCompliancePage({
    user,
    searchParams,
    buildDefaultTrainingSummary,
    mapErrorMessage,
    text: {
      loadError: TEXT.loadError,
      userSearchError: TEXT.userSearchError,
      saveRecordSuccess: TEXT.saveRecordSuccess,
      saveCertificationSuccess: TEXT.saveCertificationSuccess,
      saveRecordError: TEXT.saveRecordError,
      saveCertificationError: TEXT.saveCertificationError,
    },
  });

  const handleRecordFormFieldChange = useCallback((field, value) => {
    setRecordForm((previous) => ({ ...previous, [field]: value }));
  }, [setRecordForm]);

  const handleCertificationFormFieldChange = useCallback((field, value) => {
    setCertificationForm((previous) => ({ ...previous, [field]: value }));
  }, [setCertificationForm]);

  if (loading) {
    return <div style={{ padding: '12px' }}>{TEXT.loading}</div>;
  }

  return (
    <div style={pageContainerStyle} data-testid="training-compliance-page">
      <div style={{ ...pageHeaderStyle, justifyContent: 'flex-end' }}>
        <button type="button" onClick={loadData} style={buttonStyle}>
          {TEXT.refresh}
        </button>
      </div>

      {error ? (
        <div data-testid="training-compliance-error" style={bannerErrorStyle}>
          {error}
        </div>
      ) : null}

      {success ? (
        <div data-testid="training-compliance-success" style={bannerSuccessStyle}>
          {success}
        </div>
      ) : null}

      <TrainingRequirementsSection
        text={TEXT}
        requirements={requirements}
        getControlledActionLabel={getControlledActionLabel}
      />

      <div style={tabListStyle}>
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
        <TrainingRecordsSection
          text={TEXT}
          requirements={requirements}
          records={records}
          recordForm={recordForm}
          recordSelectedUser={recordSelectedUser}
          recordUserSearch={recordUserSearch}
          savingRecord={savingRecord}
          trainingOutcomeOptions={TRAINING_OUTCOME_OPTIONS}
          effectivenessOptions={EFFECTIVENESS_OPTIONS}
          buildRequirementOptionLabel={buildRequirementOptionLabel}
          getTrainingOutcomeLabel={getTrainingOutcomeLabel}
          getEffectivenessLabel={getEffectivenessLabel}
          buildDisplayUserLabel={buildDisplayUserLabel}
          buildUserLabel={buildUserLabel}
          formatTime={formatTime}
          onRequirementChange={applyRecordRequirementCode}
          onRecordFormFieldChange={handleRecordFormFieldChange}
          onUserKeywordChange={handleRecordUserKeywordChange}
          onOpenUserSearch={openRecordUserSearch}
          onCloseUserSearch={closeRecordUserSearch}
          onSelectUser={handleSelectRecordUser}
          onSubmit={handleCreateRecord}
        />
      ) : (
        <TrainingCertificationsSection
          text={TEXT}
          requirements={requirements}
          certifications={certifications}
          certificationForm={certificationForm}
          certificationSelectedUser={certificationSelectedUser}
          certificationUserSearch={certificationUserSearch}
          savingCertification={savingCertification}
          certificationStatusOptions={CERTIFICATION_STATUS_OPTIONS}
          buildRequirementOptionLabel={buildRequirementOptionLabel}
          getCertificationStatusLabel={getCertificationStatusLabel}
          buildDisplayUserLabel={buildDisplayUserLabel}
          buildUserLabel={buildUserLabel}
          formatTime={formatTime}
          onCertificationFormFieldChange={handleCertificationFormFieldChange}
          onUserKeywordChange={handleCertificationUserKeywordChange}
          onOpenUserSearch={openCertificationUserSearch}
          onCloseUserSearch={closeCertificationUserSearch}
          onSelectUser={handleSelectCertificationUser}
          onSubmit={handleCreateCertification}
        />
      )}
    </div>
  );
}
