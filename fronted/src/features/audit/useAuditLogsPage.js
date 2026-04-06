import { useCallback, useEffect, useMemo, useState } from 'react';
import { auditApi } from './api';
import { orgDirectoryApi } from '../orgDirectory/api';

const DEFAULT_FILTERS = {
  action: '',
  company_id: '',
  department_id: '',
  username: '',
  from: '',
  to: '',
  limit: 200,
  offset: 0,
};

const parseDateTimeLocalToMs = (value) => {
  if (!value) return null;
  const timestamp = Date.parse(value);
  return Number.isFinite(timestamp) ? timestamp : null;
};

const buildEventParams = (filters) => {
  const params = {
    limit: filters.limit || 200,
    offset: filters.offset || 0,
  };

  if (filters.action) params.action = filters.action;
  if (filters.username) params.username = filters.username;
  if (filters.company_id) params.company_id = filters.company_id;
  if (filters.department_id) params.department_id = filters.department_id;

  const fromMs = parseDateTimeLocalToMs(filters.from);
  const toMs = parseDateTimeLocalToMs(filters.to);

  if (fromMs != null) params.from_ms = String(fromMs);
  if (toMs != null) params.to_ms = String(toMs);

  return params;
};

export default function useAuditLogsPage() {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [result, setResult] = useState({ total: 0, items: [] });

  const loadLogs = useCallback(async (nextFilters) => {
    setLoading(true);
    setError('');
    try {
      const data = await auditApi.listEvents(buildEventParams(nextFilters));
      setResult({
        total: Number(data?.total || 0),
        items: Array.isArray(data?.items) ? data.items : [],
      });
    } catch (requestError) {
      setError(requestError?.message || String(requestError));
      setResult({ total: 0, items: [] });
    } finally {
      setLoading(false);
    }
  }, []);

  const loadInitialData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [companyItems, departmentItems, logs] = await Promise.all([
        orgDirectoryApi.listCompanies(),
        orgDirectoryApi.listDepartments(),
        auditApi.listEvents(buildEventParams(DEFAULT_FILTERS)),
      ]);

      setCompanies(Array.isArray(companyItems) ? companyItems : []);
      setDepartments(Array.isArray(departmentItems) ? departmentItems : []);
      setResult({
        total: Number(logs?.total || 0),
        items: Array.isArray(logs?.items) ? logs.items : [],
      });
    } catch (requestError) {
      setCompanies([]);
      setDepartments([]);
      setResult({ total: 0, items: [] });
      setError(requestError?.message || String(requestError));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadInitialData();
  }, [loadInitialData]);

  const rows = useMemo(() => result.items || [], [result.items]);

  const visibleDepartments = useMemo(() => {
    const companyId = filters.company_id ? Number(filters.company_id) : null;
    if (companyId == null) return departments;
    return departments.filter(
      (department) =>
        department.company_id == null || Number(department.company_id) === companyId
    );
  }, [departments, filters.company_id]);

  const updateFilter = useCallback((field, value) => {
    setFilters((previous) => ({
      ...previous,
      [field]: value,
    }));
  }, []);

  const applyFilters = useCallback(async () => {
    const nextFilters = {
      ...filters,
      offset: 0,
    };
    setFilters(nextFilters);
    await loadLogs(nextFilters);
  }, [filters, loadLogs]);

  const goPrev = useCallback(async () => {
    const nextFilters = {
      ...filters,
      offset: Math.max(0, (filters.offset || 0) - (filters.limit || 200)),
    };
    setFilters(nextFilters);
    await loadLogs(nextFilters);
  }, [filters, loadLogs]);

  const goNext = useCallback(async () => {
    const nextFilters = {
      ...filters,
      offset: (filters.offset || 0) + (filters.limit || 200),
    };
    setFilters(nextFilters);
    await loadLogs(nextFilters);
  }, [filters, loadLogs]);

  return {
    loading,
    error,
    companies,
    departments,
    filters,
    result,
    rows,
    visibleDepartments,
    canGoPrev: (filters.offset || 0) > 0,
    canGoNext: (filters.offset || 0) + rows.length < result.total,
    updateFilter,
    applyFilters,
    goPrev,
    goNext,
  };
}
