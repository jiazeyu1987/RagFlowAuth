export const MOBILE_BREAKPOINT = 768;

export const isRunningStatus = (status) =>
  ['queued', 'running', 'canceling'].includes(String(status || '').toLowerCase());

export const formatTime = (ms) => {
  if (!ms) return '';
  const value = new Date(Number(ms));
  return Number.isNaN(value.getTime()) ? '' : value.toLocaleString();
};

export const getLocalBackupTargetPath = (settings) => String(settings?.local_backup_target_path || '');

export const getStatusColor = (status) => {
  const text = String(status || '').toLowerCase();
  if (text === 'failed') return '#dc2626';
  if (text === 'completed' || text === 'success' || text === 'succeeded') return '#059669';
  if (isRunningStatus(text) || text === 'pending') return '#2563eb';
  return '#374151';
};

export const getLocalBackupLabel = (job) => {
  if (job?.output_dir) return '成功';
  if (String(job?.status || '').toLowerCase() === 'failed') return '失败';
  return '未生成';
};

export const getRestoreEligibleJobs = (jobs) =>
  (jobs || []).filter((job) => Boolean(String(job?.output_dir || '').trim()));

export const pickRestoreJobId = (jobs, previousValue = '') => {
  const eligibleJobs = getRestoreEligibleJobs(jobs);
  if (previousValue && eligibleJobs.some((job) => String(job.id) === String(previousValue))) {
    return String(previousValue);
  }
  return eligibleJobs[0] ? String(eligibleJobs[0].id) : '';
};

export const getRestoreJobById = (jobs, selectedRestoreJobId) => {
  const eligibleJobs = getRestoreEligibleJobs(jobs);
  const id = Number(selectedRestoreJobId);
  if (!Number.isFinite(id) || id <= 0) return null;
  return eligibleJobs.find((job) => Number(job.id) === id) || null;
};
