import { useCallback, useEffect, useRef, useState } from 'react';
import { dataSecurityApi } from './api';
import { isRunningStatus } from './dataSecurityHelpers';

export default function useDataSecurityJobs() {
  const [jobs, setJobs] = useState([]);
  const [restoreDrills, setRestoreDrills] = useState([]);
  const [activeJob, setActiveJob] = useState(null);
  const [running, setRunning] = useState(false);
  const pollTimer = useRef(null);

  const stopPolling = useCallback(() => {
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
  }, []);

  const refreshJobsAndDrills = useCallback(async () => {
    const [nextJobs, nextDrills] = await Promise.all([
      dataSecurityApi.listJobs(30),
      dataSecurityApi.listRestoreDrills(30),
    ]);
    setJobs(nextJobs);
    setRestoreDrills(nextDrills);
    return { jobs: nextJobs, restoreDrills: nextDrills };
  }, []);

  const pollActiveJob = useCallback(
    async (jobId) => {
      try {
        const job = await dataSecurityApi.getJob(jobId);
        setActiveJob(job);
        const nextRunning = isRunningStatus(job?.status);
        setRunning(nextRunning);
        if (!nextRunning) {
          await refreshJobsAndDrills();
          stopPolling();
        }
        return nextRunning;
      } catch {
        return true;
      }
    },
    [refreshJobsAndDrills, stopPolling]
  );

  const loadJobsAndDrills = useCallback(async () => {
    const { jobs: nextJobs, restoreDrills: nextDrills } = await refreshJobsAndDrills();
    const latestJob = nextJobs[0] || null;
    setActiveJob(latestJob);
    setRunning(latestJob ? isRunningStatus(latestJob.status) : false);
    return { jobs: nextJobs, restoreDrills: nextDrills, latestJob };
  }, [refreshJobsAndDrills]);

  const startPollingJob = useCallback(
    async (jobId) => {
      stopPolling();
      setRunning(true);
      const nextRunning = await pollActiveJob(jobId);
      if (nextRunning) {
        pollTimer.current = setInterval(() => {
          pollActiveJob(jobId);
        }, 1000);
      }
    },
    [pollActiveJob, stopPolling]
  );

  const handleSelectJob = useCallback(
    (job) => {
      stopPolling();
      setActiveJob(job);
      const nextRunning = isRunningStatus(job?.status);
      setRunning(nextRunning);
      if (nextRunning) {
        pollTimer.current = setInterval(() => {
          pollActiveJob(job.id);
        }, 1000);
      }
    },
    [pollActiveJob, stopPolling]
  );

  useEffect(() => () => stopPolling(), [stopPolling]);

  return {
    jobs,
    restoreDrills,
    activeJob,
    running,
    refreshJobsAndDrills,
    loadJobsAndDrills,
    startPollingJob,
    handleSelectJob,
  };
}
