import React from 'react';

import OrgAuditPanel from '../features/orgDirectory/components/OrgAuditPanel';
import OrgOverviewPanel from '../features/orgDirectory/components/OrgOverviewPanel';
import OrgTabButton from '../features/orgDirectory/components/OrgTabButton';
import OrgTreePanel from '../features/orgDirectory/components/OrgTreePanel';
import { AUDIT_TAB, OVERVIEW_TAB } from '../features/orgDirectory/helpers';
import { panelStyle } from '../features/orgDirectory/pageStyles';
import useOrgDirectoryManagementPage from '../features/orgDirectory/useOrgDirectoryManagementPage';

const alertStyle = {
  borderRadius: 8,
  padding: '10px 12px',
  marginBottom: 16,
};

export default function OrgDirectoryManagement() {
  const {
    excelFileInputRef,
    isMobile,
    activeTab,
    setActiveTab,
    loading,
    rebuilding,
    error,
    notice,
    auditError,
    tree,
    companies,
    departments,
    auditLogs,
    latestOverviewAudit,
    auditFilter,
    setAuditFilter,
    searchTerm,
    selectedSearchKey,
    selectedPersonNodeKey,
    selectedPersonEntry,
    highlightedNodeKey,
    expandedKeys,
    selectedExcelFile,
    recipientMapRebuildSummary,
    personColumnCount,
    personCount,
    isMissingPersonNodes,
    canTriggerRebuild,
    trimmedSearchTerm,
    totalSearchMatches,
    searchResults,
    registerNodeRef,
    refreshAudit,
    handleSearchInputChange,
    handleClearSearch,
    handleSelectSearchResult,
    handleSelectPerson,
    handleToggleBranch,
    handleChooseExcelFile,
    handleClearExcelFile,
    handleExcelFileChange,
    handleRebuild,
  } = useOrgDirectoryManagementPage();

  if (loading) return <div>加载中...</div>;

  return (
    <div data-testid="org-page">
      {error ? (
        <div
          data-testid="org-error"
          style={{
            ...alertStyle,
            color: '#991b1b',
            backgroundColor: '#fee2e2',
            border: '1px solid #fecaca',
          }}
        >
          错误: {error}
        </div>
      ) : null}

      {notice ? (
        <div
          data-testid="org-notice"
          style={{
            ...alertStyle,
            color: '#166534',
            backgroundColor: '#f0fdf4',
            border: '1px solid #86efac',
          }}
        >
          {notice}
        </div>
      ) : null}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'minmax(0, 1.95fr) minmax(340px, 1fr)',
          gap: 16,
          alignItems: 'start',
        }}
      >
        <OrgTreePanel
          isMobile={isMobile}
          tree={tree}
          isMissingPersonNodes={isMissingPersonNodes}
          expandedKeys={expandedKeys}
          handleToggleBranch={handleToggleBranch}
          handleSelectPerson={handleSelectPerson}
          highlightedNodeKey={highlightedNodeKey}
          selectedPersonNodeKey={selectedPersonNodeKey}
          personColumnCount={personColumnCount}
          registerNodeRef={registerNodeRef}
        />

        <div
          style={{
            ...panelStyle,
            padding: isMobile ? 14 : 18,
            minWidth: 0,
            position: isMobile ? 'static' : 'sticky',
            top: 16,
          }}
        >
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
              gap: 8,
              marginBottom: 14,
            }}
          >
            <OrgTabButton
              active={activeTab === OVERVIEW_TAB}
              dataTestId="org-tab-overview"
              onClick={() => setActiveTab(OVERVIEW_TAB)}
            >
              概览
            </OrgTabButton>
            <OrgTabButton
              active={activeTab === AUDIT_TAB}
              dataTestId="org-tab-audit"
              onClick={() => setActiveTab(AUDIT_TAB)}
            >
              审计
            </OrgTabButton>
          </div>

          {activeTab === OVERVIEW_TAB ? (
            <OrgOverviewPanel
              isMobile={isMobile}
              excelFileInputRef={excelFileInputRef}
              rebuilding={rebuilding}
              searchTerm={searchTerm}
              selectedSearchKey={selectedSearchKey}
              selectedPersonEntry={selectedPersonEntry}
              selectedExcelFile={selectedExcelFile}
              recipientMapRebuildSummary={recipientMapRebuildSummary}
              personCount={personCount}
              companies={companies}
              departments={departments}
              latestOverviewAudit={latestOverviewAudit}
              isMissingPersonNodes={isMissingPersonNodes}
              canTriggerRebuild={canTriggerRebuild}
              trimmedSearchTerm={trimmedSearchTerm}
              totalSearchMatches={totalSearchMatches}
              searchResults={searchResults}
              handleSearchInputChange={handleSearchInputChange}
              handleClearSearch={handleClearSearch}
              handleSelectSearchResult={handleSelectSearchResult}
              handleChooseExcelFile={handleChooseExcelFile}
              handleClearExcelFile={handleClearExcelFile}
              handleExcelFileChange={handleExcelFileChange}
              handleRebuild={handleRebuild}
            />
          ) : (
            <OrgAuditPanel
              isMobile={isMobile}
              auditFilter={auditFilter}
              setAuditFilter={setAuditFilter}
              refreshAudit={refreshAudit}
              auditError={auditError}
              auditLogs={auditLogs}
            />
          )}
        </div>
      </div>
    </div>
  );
}
