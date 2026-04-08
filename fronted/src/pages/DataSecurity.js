import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import useDataSecurityPage from '../features/dataSecurity/useDataSecurityPage';
import { MOBILE_BREAKPOINT } from '../features/dataSecurity/dataSecurityHelpers';
import DataSecurityRetentionSection from '../features/dataSecurity/components/DataSecurityRetentionSection';
import DataSecuritySettingsSection from '../features/dataSecurity/components/DataSecuritySettingsSection';
import DataSecurityActiveJobSection from '../features/dataSecurity/components/DataSecurityActiveJobSection';
import DataSecurityJobListSection from '../features/dataSecurity/components/DataSecurityJobListSection';
import DataSecurityRestoreDrillsSection from '../features/dataSecurity/components/DataSecurityRestoreDrillsSection';

export default function DataSecurity() {
  const location = useLocation();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  const showAdvanced = useMemo(
    () => new URLSearchParams(location.search).get('advanced') === '1',
    [location.search]
  );

  const {
    loading,
    running,
    error,
    settings,
    jobs,
    activeJob,
    savingSettings,
    savingRetention,
    restoreDrills,
    localBackupTargetPath,
    restoreEligibleJobs,
    selectedRestoreJobId,
    restoreTarget,
    restoreNotes,
    creatingRestoreDrill,
    setSettingField,
    setSelectedRestoreJobId,
    setRestoreTarget,
    setRestoreNotes,
    saveSettings,
    saveRetention,
    runNow,
    runFullBackupNow,
    handleSelectJob,
    submitRestoreDrill,
  } = useDataSecurityPage();

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleSaveRetention = useCallback(async () => {
    const changeReason = window.prompt('请输入本次备份保留策略变更原因');
    if (changeReason === null) return;
    await saveRetention(changeReason);
  }, [saveRetention]);

  const handleSaveSettings = useCallback(async () => {
    const changeReason = window.prompt('请输入本次备份高级设置变更原因');
    if (changeReason === null) return;
    await saveSettings(changeReason);
  }, [saveSettings]);

  if (loading) return <div style={{ padding: '12px' }}>加载中...</div>;

  return (
    <div style={{ maxWidth: '980px', width: '100%' }} data-testid="data-security-page">
      <div
        style={{
          display: 'flex',
          flexDirection: isMobile ? 'column' : 'row',
          justifyContent: 'flex-end',
          gap: '12px',
          alignItems: isMobile ? 'stretch' : 'center',
        }}
      >
        <div
          style={{
            display: 'flex',
            flexDirection: isMobile ? 'column' : 'row',
            gap: '10px',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          <button
            onClick={runNow}
            disabled={running}
            data-testid="ds-run-now"
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: 'none',
              cursor: running ? 'not-allowed' : 'pointer',
              background: running ? '#9ca3af' : '#3b82f6',
              color: 'white',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {running ? '备份中...' : '立即备份'}
          </button>
          <button
            onClick={runFullBackupNow}
            disabled={running}
            data-testid="ds-run-full"
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: 'none',
              cursor: running ? 'not-allowed' : 'pointer',
              background: running ? '#9ca3af' : '#8b5cf6',
              color: 'white',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {running ? '备份中...' : '全量备份'}
          </button>
        </div>
      </div>

      {error ? (
        <div
          data-testid="ds-error"
          style={{
            marginTop: '12px',
            padding: '10px 12px',
            background: '#fef2f2',
            color: '#991b1b',
            borderRadius: '10px',
          }}
        >
          {error}
        </div>
      ) : null}

      <DataSecurityRetentionSection
        isMobile={isMobile}
        settings={settings}
        localBackupTargetPath={localBackupTargetPath}
        onSettingFieldChange={setSettingField}
        onSaveRetention={handleSaveRetention}
        savingRetention={savingRetention}
      />

      {showAdvanced ? (
        <DataSecuritySettingsSection
          isMobile={isMobile}
          settings={settings}
          localBackupTargetPath={localBackupTargetPath}
          onSettingFieldChange={setSettingField}
          onSaveSettings={handleSaveSettings}
          savingSettings={savingSettings}
        />
      ) : null}

      <DataSecurityActiveJobSection activeJob={activeJob} isMobile={isMobile} />
      <DataSecurityJobListSection jobs={jobs} isMobile={isMobile} onSelectJob={handleSelectJob} />
      <DataSecurityRestoreDrillsSection
        isMobile={isMobile}
        restoreEligibleJobs={restoreEligibleJobs}
        selectedRestoreJobId={selectedRestoreJobId}
        restoreTarget={restoreTarget}
        restoreNotes={restoreNotes}
        restoreDrills={restoreDrills}
        creatingRestoreDrill={creatingRestoreDrill}
        onSelectedRestoreJobIdChange={setSelectedRestoreJobId}
        onRestoreTargetChange={setRestoreTarget}
        onRestoreNotesChange={setRestoreNotes}
        onSubmit={submitRestoreDrill}
      />
    </div>
  );
}
