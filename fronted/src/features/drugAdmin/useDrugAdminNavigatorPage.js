import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import drugAdminApi from './api';

const MOBILE_BREAKPOINT = 768;

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

const normalizeProvinceList = (provinces) => (
  Array.isArray(provinces) ? provinces.filter((item) => String(item?.name || '').trim()) : []
);

export default function useDrugAdminNavigatorPage() {
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [validatedOn, setValidatedOn] = useState('');
  const [source, setSource] = useState('');
  const [provinces, setProvinces] = useState([]);
  const [selectedProvince, setSelectedProvince] = useState('');
  const [lastResolve, setLastResolve] = useState(null);
  const [verifyResult, setVerifyResult] = useState(null);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    let active = true;

    const loadProvinces = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await drugAdminApi.listProvinces();
        if (!active) return;

        const list = normalizeProvinceList(data?.provinces);
        setValidatedOn(String(data?.validated_on || ''));
        setSource(String(data?.source || ''));
        setProvinces(list);
        setSelectedProvince((previous) => {
          const current = String(previous || '').trim();
          if (current && list.some((item) => String(item?.name || '').trim() === current)) {
            return current;
          }
          return String(list[0]?.name || '');
        });
      } catch (requestError) {
        if (!active) return;
        setProvinces([]);
        setSelectedProvince('');
        setError(requestError?.message || '加载省份列表失败');
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadProvinces();
    return () => {
      active = false;
    };
  }, []);

  const openSelected = useCallback(async () => {
    if (!selectedProvince) return;

    setActionLoading(true);
    setError('');
    setInfo(`正在检查 ${selectedProvince}...`);

    try {
      const result = await drugAdminApi.resolveProvince(selectedProvince);
      setLastResolve(result);
      if (result?.ok && result?.url) {
        window.open(result.url, '_blank', 'noopener,noreferrer');
        setInfo(`${selectedProvince} 可访问 (HTTP ${result?.code || '-'})`);
      } else {
        setInfo(`${selectedProvince} 当前不可访问`);
      }
    } catch (requestError) {
      setError(requestError?.message || '省份链接解析失败');
    } finally {
      setActionLoading(false);
    }
  }, [selectedProvince]);

  const verifyAll = useCallback(async () => {
    setVerifying(true);
    setError('');
    setInfo('正在校验全部省份站点...');

    try {
      const result = await drugAdminApi.verifyAll();
      setVerifyResult(result);
      setInfo(
        `校验完成：共 ${result?.total || 0} 个，成功 ${result?.success || 0} 个，失败 ${result?.failed || 0} 个`
      );
    } catch (requestError) {
      setError(requestError?.message || '批量校验失败');
    } finally {
      setVerifying(false);
    }
  }, []);

  const failedRows = useMemo(
    () => (Array.isArray(verifyResult?.rows) ? verifyResult.rows.filter((row) => !row?.ok) : []),
    [verifyResult]
  );

  const goBack = useCallback(() => {
    navigate('/tools');
  }, [navigate]);

  return {
    isMobile,
    loading,
    actionLoading,
    verifying,
    error,
    info,
    validatedOn,
    source,
    provinces,
    selectedProvince,
    lastResolve,
    verifyResult,
    failedRows,
    setSelectedProvince,
    openSelected,
    verifyAll,
    goBack,
  };
}
