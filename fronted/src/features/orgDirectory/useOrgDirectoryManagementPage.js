import { useEffect, useRef, useState } from 'react';

import useOrgDirectoryData from './useOrgDirectoryData';
import useOrgDirectoryRebuild from './useOrgDirectoryRebuild';
import useOrgDirectorySearchState from './useOrgDirectorySearchState';
import { MOBILE_BREAKPOINT, OVERVIEW_TAB } from './helpers';

export default function useOrgDirectoryManagementPage() {
  const nodeRefs = useRef(new Map());
  const excelFileInputRef = useRef(null);

  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [activeTab, setActiveTab] = useState(OVERVIEW_TAB);
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);

  const {
    loading,
    auditError,
    tree,
    companies,
    departments,
    auditLogs,
    latestOverviewAudit,
    auditFilter,
    setAuditFilter,
    loadAll,
    refreshAudit,
  } = useOrgDirectoryData({ setError });

  const {
    searchTerm,
    selectedSearchKey,
    selectedPersonNodeKey,
    selectedPersonEntry,
    highlightedNodeKey,
    expandedKeys,
    personColumnCount,
    personCount,
    isMissingPersonNodes,
    trimmedSearchTerm,
    totalSearchMatches,
    searchResults,
    registerNodeRef,
    resetAfterRebuild,
    handleSearchInputChange,
    handleClearSearch,
    handleSelectSearchResult,
    handleSelectPerson,
    handleToggleBranch,
  } = useOrgDirectorySearchState({
    tree,
    companies,
    departments,
    isMobile,
    nodeRefs,
    setActiveTab,
  });

  const {
    rebuilding,
    selectedExcelFile,
    recipientMapRebuildSummary,
    canTriggerRebuild,
    handleChooseExcelFile,
    handleClearExcelFile,
    handleExcelFileChange,
    handleRebuild,
  } = useOrgDirectoryRebuild({
    excelFileInputRef,
    loadAll,
    resetAfterRebuild,
    setError,
    setNotice,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  return {
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
  };
}
