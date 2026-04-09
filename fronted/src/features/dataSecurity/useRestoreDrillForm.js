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
  const [creatingRealRestore, setCreatingRealRestore] = useState(false);

  const restoreEligibleJobs = useMemo(() => getRestoreEligibleJobs(jobs), [jobs]);
  const selectedRestoreJobId = useMemo(
    () => pickRestoreJobId(jobs, selectedRestoreJobIdState),
    [jobs, selectedRestoreJobIdState]
  );
  const selectedRestoreJob = useMemo(
    () => getRestoreJobById(jobs, selectedRestoreJobId),
    [jobs, selectedRestoreJobId]
  );

  const restoreDrillBlockedReason = useMemo(() => {
    if (restoreEligibleJobs.length === 0) {
      return '当前没有可用于恢复的服务器本机备份任务，请先执行一次本机备份。';
    }
    if (!selectedRestoreJob) {
      return '请先选择一条可用于恢复的服务器本机备份任务。';
    }
    if (!selectedRestoreJob.output_dir) {
      return '所选任务没有服务器本机备份目录，无法执行恢复。';
    }
    if (!selectedRestoreJob.package_hash) {
      return '所选任务缺少 package_hash，无法执行恢复。';
    }
    return '';
  }, [restoreEligibleJobs, selectedRestoreJob]);

  const canSubmitRestoreDrill = !restoreDrillBlockedReason;
  const canSubmitRealRestore = !restoreDrillBlockedReason;

  const setSelectedRestoreJobId = useCallback((value) => {
    setSelectedRestoreJobIdState(String(value || ''));
  }, []);

  const submitRestoreDrill = useCallback(async () => {
    onError(null);
    if (restoreDrillBlockedReason) {
      onError(restoreDrillBlockedReason);
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
  }, [
    onError,
    refreshJobsAndDrills,
    restoreDrillBlockedReason,
    restoreNotes,
    restoreTarget,
    selectedRestoreJob,
  ]);

  const submitRealRestore = useCallback(
    async ({ changeReason, confirmationText }) => {
      onError(null);
      if (restoreDrillBlockedReason) {
        onError(restoreDrillBlockedReason);
        return null;
      }

      const trimmedReason = String(changeReason || '').trim();
      if (!trimmedReason) {
        onError('恢复原因不能为空');
        return null;
      }

      const trimmedConfirmation = String(confirmationText || '').trim();
      if (!trimmedConfirmation) {
        onError('请输入 RESTORE 以确认真实恢复');
        return null;
      }

      setCreatingRealRestore(true);
      try {
        const result = await dataSecurityApi.runRealRestore({
          job_id: Number(selectedRestoreJob.id),
          backup_path: selectedRestoreJob.output_dir,
          backup_hash: selectedRestoreJob.package_hash,
          change_reason: trimmedReason,
          confirmation_text: trimmedConfirmation,
        });
        await refreshJobsAndDrills();
        setRestoreNotes('');
        return result;
      } catch (e) {
        onError(e.message || '真实恢复失败');
        return null;
      } finally {
        setCreatingRealRestore(false);
      }
    },
    [onError, refreshJobsAndDrills, restoreDrillBlockedReason, selectedRestoreJob]
  );

  return {
    restoreDrillsLoading: creatingRestoreDrill,
    restoreEligibleJobs,
    selectedRestoreJobId,
    selectedRestoreJob,
    restoreDrillBlockedReason,
    canSubmitRestoreDrill,
    canSubmitRealRestore,
    restoreTarget,
    restoreNotes,
    creatingRestoreDrill,
    creatingRealRestore,
    setSelectedRestoreJobId,
    setRestoreTarget,
    setRestoreNotes,
    submitRestoreDrill,
    submitRealRestore,
  };
}
