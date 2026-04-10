import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import useDataSecurityPage from '../features/dataSecurity/useDataSecurityPage';
import { MOBILE_BREAKPOINT } from '../features/dataSecurity/dataSecurityHelpers';
import DataSecurityRetentionSection from '../features/dataSecurity/components/DataSecurityRetentionSection';
import DataSecuritySettingsSection from '../features/dataSecurity/components/DataSecuritySettingsSection';
import DataSecurityActiveJobSection from '../features/dataSecurity/components/DataSecurityActiveJobSection';
import DataSecurityJobListSection from '../features/dataSecurity/components/DataSecurityJobListSection';
import DataSecurityRestoreDrillsSection from '../features/dataSecurity/components/DataSecurityRestoreDrillsSection';

export default function DataSecurity() {
  const location = useLocation();
  const navigate = useNavigate();
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
    restoreDrillBlockedReason,
    canSubmitRestoreDrill,
    canSubmitRealRestore,
    restoreTarget,
    restoreNotes,
    creatingRestoreDrill,
    creatingRealRestore,
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
    submitRealRestore,
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

  const handleSubmitRealRestore = useCallback(async () => {
    const changeReason = window.prompt('请输入本次真实恢复原因');
    if (changeReason === null) return;
    const confirmationText = window.prompt(
      '此操作会覆盖当前系统数据。请输入 RESTORE 确认恢复'
    );
    if (confirmationText === null) return;
    const result = await submitRealRestore({
      changeReason,
      confirmationText,
    });
    if (result) {
      window.alert(`真实恢复已完成：${result.live_auth_db_path}`);
    }
  }, [submitRealRestore]);

  const handleToggleAdvanced = useCallback(() => {
    const params = new URLSearchParams(location.search);
    if (showAdvanced) {
      params.delete('advanced');
    } else {
      params.set('advanced', '1');
    }
    const nextSearch = params.toString();
    navigate(
      {
        pathname: location.pathname,
        search: nextSearch ? `?${nextSearch}` : '',
      },
      { replace: false }
    );
  }, [location.pathname, location.search, navigate, showAdvanced]);

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
          <button
            type="button"
            onClick={handleToggleAdvanced}
            data-testid="ds-toggle-advanced"
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid #d1d5db',
              cursor: 'pointer',
              background: showAdvanced ? '#f3f4f6' : 'white',
              color: '#111827',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            {showAdvanced ? '收起高级设置' : '高级设置'}
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
        restoreDrillBlockedReason={restoreDrillBlockedReason}
        canSubmitRestoreDrill={canSubmitRestoreDrill}
        canSubmitRealRestore={canSubmitRealRestore}
        restoreTarget={restoreTarget}
        restoreNotes={restoreNotes}
        restoreDrills={restoreDrills}
        creatingRestoreDrill={creatingRestoreDrill}
        creatingRealRestore={creatingRealRestore}
        onSelectedRestoreJobIdChange={setSelectedRestoreJobId}
        onRestoreTargetChange={setRestoreTarget}
        onRestoreNotesChange={setRestoreNotes}
        onSubmit={submitRestoreDrill}
        onRealRestoreSubmit={handleSubmitRealRestore}
      />
    </div>
  );
}
