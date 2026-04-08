import { useCallback, useMemo, useState } from 'react';
import { dataSecurityApi } from './api';
import {
  getRestoreEligibleJobs,
  getRestoreJobById,
  pickRestoreJobId,
} from './dataSecurityHelpers';

export default function useRestoreDrillForm({ jobs, refreshJobsAndDrills, onError }) {
  const [selectedRestoreJobIdState, setSelectedRestoreJobIdState] = useState('');
  const [restoreTarget, setRestoreTarget] = useState('staging');
  const [restoreNotes, setRestoreNotes] = useState('');
  const [creatingRestoreDrill, setCreatingRestoreDrill] = useState(false);

  const restoreEligibleJobs = useMemo(() => getRestoreEligibleJobs(jobs), [jobs]);
  const selectedRestoreJobId = useMemo(
    () => pickRestoreJobId(jobs, selectedRestoreJobIdState),
    [jobs, selectedRestoreJobIdState]
  );
  const selectedRestoreJob = useMemo(
    () => getRestoreJobById(jobs, selectedRestoreJobId),
    [jobs, selectedRestoreJobId]
  );

  const setSelectedRestoreJobId = useCallback((value) => {
    setSelectedRestoreJobIdState(String(value || ''));
  }, []);

  const submitRestoreDrill = useCallback(async () => {
    onError(null);
    if (!selectedRestoreJob) {
      onError('请先选择可用于恢复演练的服务器本机备份任务');
      return false;
    }
    if (!selectedRestoreJob.output_dir) {
      onError('所选任务没有服务器本机备份目录，无法执行恢复演练');
      return false;
    }
    if (!selectedRestoreJob.package_hash) {
      onError('所选任务缺少 package_hash，无法执行恢复演练');
      return false;
    }
    if (!restoreTarget.trim()) {
      onError('恢复目标不能为空');
      return false;
    }

    setCreatingRestoreDrill(true);
    try {
      await dataSecurityApi.createRestoreDrill({
        job_id: Number(selectedRestoreJob.id),
        backup_path: selectedRestoreJob.output_dir,
        backup_hash: selectedRestoreJob.package_hash,
        restore_target: restoreTarget.trim(),
        verification_notes: restoreNotes.trim(),
      });
      await refreshJobsAndDrills();
      setRestoreNotes('');
      return true;
    } catch (e) {
      onError(e.message || '恢复演练记录失败');
      return false;
    } finally {
      setCreatingRestoreDrill(false);
    }
  }, [onError, refreshJobsAndDrills, restoreNotes, restoreTarget, selectedRestoreJob]);

  return {
    restoreDrillsLoading: creatingRestoreDrill,
    restoreEligibleJobs,
    selectedRestoreJobId,
    selectedRestoreJob,
    restoreTarget,
    restoreNotes,
    creatingRestoreDrill,
    setSelectedRestoreJobId,
    setRestoreTarget,
    setRestoreNotes,
    submitRestoreDrill,
  };
}
