import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { orgDirectoryApi } from './api';
import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';
import {
  ORG_AUDIT_LOAD_ERROR,
  ORG_TREE_LOAD_ERROR,
  buildAuditParams,
} from './helpers';

export default function useOrgDirectoryData({ setError }) {
  const auditFilterRef = useRef({ entity_type: '', action: '', limit: 200 });

  const [loading, setLoading] = useState(true);
  const [auditError, setAuditError] = useState(null);
  const [tree, setTree] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [overviewAuditLogs, setOverviewAuditLogs] = useState([]);
  const [auditFilter, setAuditFilter] = useState({ entity_type: '', action: '', limit: 200 });

  useEffect(() => {
    auditFilterRef.current = auditFilter;
  }, [auditFilter]);

  const latestOverviewAudit = useMemo(
    () => (overviewAuditLogs.length > 0 ? overviewAuditLogs[0] : null),
    [overviewAuditLogs]
  );

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError(null);
    setAuditError(null);

    try {
      const [treeResult, companyResult, departmentResult, tableAuditResult, overviewAuditResult] =
        await Promise.allSettled([
          orgDirectoryApi.getTree(),
          orgDirectoryApi.listCompanies(),
          orgDirectoryApi.listDepartments(),
          orgDirectoryApi.listAudit(buildAuditParams(auditFilterRef.current)),
          orgDirectoryApi.listAudit({ limit: 200 }),
        ]);

      if (treeResult.status === 'fulfilled') {
        setTree(Array.isArray(treeResult.value) ? treeResult.value : []);
      } else {
        setTree([]);
      }

      if (companyResult.status === 'fulfilled') {
        setCompanies(Array.isArray(companyResult.value) ? companyResult.value : []);
      } else {
        setCompanies([]);
      }

      if (departmentResult.status === 'fulfilled') {
        setDepartments(Array.isArray(departmentResult.value) ? departmentResult.value : []);
      } else {
        setDepartments([]);
      }

      if (tableAuditResult.status === 'fulfilled') {
        setAuditLogs(Array.isArray(tableAuditResult.value) ? tableAuditResult.value : []);
      } else {
        setAuditLogs([]);
        setAuditError(
          tableAuditResult.reason?.message ||
            String(tableAuditResult.reason || ORG_AUDIT_LOAD_ERROR)
        );
      }

      if (overviewAuditResult.status === 'fulfilled') {
        setOverviewAuditLogs(Array.isArray(overviewAuditResult.value) ? overviewAuditResult.value : []);
      } else {
        setOverviewAuditLogs([]);
      }

      if (
        treeResult.status === 'rejected' ||
        companyResult.status === 'rejected' ||
        departmentResult.status === 'rejected'
      ) {
        const firstError =
          treeResult.status === 'rejected'
            ? treeResult.reason
            : companyResult.status === 'rejected'
              ? companyResult.reason
              : departmentResult.reason;
        setError(firstError?.message || String(firstError || ORG_TREE_LOAD_ERROR));
      }
    } finally {
      setLoading(false);
    }
  }, [setError]);

  const refreshAudit = useCallback(async (nextFilter = auditFilterRef.current) => {
    setAuditError(null);
    try {
      const data = await orgDirectoryApi.listAudit(buildAuditParams(nextFilter));
      setAuditLogs(Array.isArray(data) ? data : []);
    } catch (err) {
      setAuditLogs([]);
      setAuditError(mapUserFacingErrorMessage(err?.message, ORG_AUDIT_LOAD_ERROR));
    }
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  return {
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
  };
}
