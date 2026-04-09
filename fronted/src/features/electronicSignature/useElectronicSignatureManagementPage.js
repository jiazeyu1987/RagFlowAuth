import { useCallback, useEffect, useState } from 'react';

import { electronicSignatureApi } from './api';
import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';

const MOBILE_BREAKPOINT = 768;

const INITIAL_FILTERS = {
  record_type: '',
  action: '',
  signed_by: '',
  signed_at_from: '',
  signed_at_to: '',
};

const MESSAGES = {
  loadError: '加载电子签名数据失败',
  detailError: '加载签名详情失败',
  verifyError: '验签失败',
  verifyPassed: '验签通过',
  verifyFailed: '验签未通过',
  notSelected: '请先选择一条签名记录',
  authorizationLoadError: '加载签名授权失败',
  authorizationUpdateError: '更新签名授权失败',
};

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

const toTimestampMs = (value, endOfMinute = false) => {
  const text = String(value || '').trim();
  if (!text) return undefined;
  const normalized = endOfMinute ? `${text}:59` : `${text}:00`;
  const timestamp = new Date(normalized).getTime();
  return Number.isFinite(timestamp) ? timestamp : undefined;
};

const getItems = (payload) => (Array.isArray(payload?.items) ? payload.items : []);

export default function useElectronicSignatureManagementPage() {
  const [activeTab, setActiveTab] = useState('signatures');
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [error, setError] = useState('');
  const [verifyMessage, setVerifyMessage] = useState('');
  const [filters, setFilters] = useState(INITIAL_FILTERS);
  const [displaySignatures, setDisplaySignatures] = useState([]);
  const [total, setTotal] = useState(0);
  const [selectedSignatureId, setSelectedSignatureId] = useState('');
  const [selectedSignature, setSelectedSignature] = useState(null);
  const [authorizationLoading, setAuthorizationLoading] = useState(true);
  const [authorizations, setAuthorizations] = useState([]);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const loadSignatures = useCallback(async (nextFilters, currentSelectedSignatureId = '') => {
    setError('');
    setVerifyMessage('');
    setLoading(true);

    try {
      const response = await electronicSignatureApi.listSignatures({
        record_type: nextFilters?.record_type,
        action: nextFilters?.action,
        signed_by: nextFilters?.signed_by,
        signed_at_from_ms: toTimestampMs(nextFilters?.signed_at_from, false),
        signed_at_to_ms: toTimestampMs(nextFilters?.signed_at_to, true),
        limit: 100,
        offset: 0,
      });

      const items = getItems(response);
      setDisplaySignatures(items);
      setTotal(Number(response?.total || 0));

      if (items.length === 0) {
        setSelectedSignatureId('');
        setSelectedSignature(null);
        return;
      }

      const nextSignatureId = items.some(
        (item) => item.signature_id === currentSelectedSignatureId
      )
        ? currentSelectedSignatureId
        : items[0].signature_id;

      setSelectedSignatureId(nextSignatureId);
      const detail = await electronicSignatureApi.getSignature(nextSignatureId);
      setSelectedSignature(detail);
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, MESSAGES.loadError));
    } finally {
      setLoading(false);
    }
  }, []);

  const loadAuthorizations = useCallback(async () => {
    setAuthorizationLoading(true);

    try {
      const response = await electronicSignatureApi.listAuthorizations({ limit: 200 });
      setAuthorizations(getItems(response));
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, MESSAGES.authorizationLoadError));
    } finally {
      setAuthorizationLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSignatures(INITIAL_FILTERS);
  }, [loadSignatures]);

  useEffect(() => {
    loadAuthorizations();
  }, [loadAuthorizations]);

  const setFilterValue = useCallback((key, value) => {
    setFilters((previous) => ({
      ...previous,
      [key]: value,
    }));
  }, []);

  const handleSearch = useCallback(async () => {
    await loadSignatures(filters, selectedSignatureId);
  }, [filters, loadSignatures, selectedSignatureId]);

  const handleReset = useCallback(async () => {
    setFilters(INITIAL_FILTERS);
    await loadSignatures(INITIAL_FILTERS);
  }, [loadSignatures]);

  const handleSelectSignature = useCallback(async (signatureId) => {
    setSelectedSignatureId(signatureId);
    setDetailLoading(true);
    setError('');
    setVerifyMessage('');

    try {
      const detail = await electronicSignatureApi.getSignature(signatureId);
      setSelectedSignature(detail);
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, MESSAGES.detailError));
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const handleVerifySignature = useCallback(async () => {
    if (!selectedSignatureId) {
      setError(MESSAGES.notSelected);
      return;
    }

    setVerifyLoading(true);
    setError('');
    setVerifyMessage('');

    try {
      const result = await electronicSignatureApi.verifySignature(selectedSignatureId);
      const verified = Boolean(result?.verified);

      setSelectedSignature((previous) => (previous ? { ...previous, verified } : previous));
      setDisplaySignatures((previous) =>
        previous.map((item) =>
          item.signature_id === selectedSignatureId ? { ...item, verified } : item
        )
      );
      setVerifyMessage(verified ? MESSAGES.verifyPassed : MESSAGES.verifyFailed);
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, MESSAGES.verifyError));
    } finally {
      setVerifyLoading(false);
    }
  }, [selectedSignatureId]);

  const handleToggleAuthorization = useCallback(
    async (userId, nextEnabled) => {
      setError('');

      try {
        await electronicSignatureApi.updateAuthorization(userId, {
          electronic_signature_enabled: nextEnabled,
        });
        await loadAuthorizations();
      } catch (requestError) {
        setError(mapUserFacingErrorMessage(requestError?.message, MESSAGES.authorizationUpdateError));
      }
    },
    [loadAuthorizations]
  );

  return {
    activeTab,
    isMobile,
    loading,
    detailLoading,
    verifyLoading,
    error,
    verifyMessage,
    filters,
    displaySignatures,
    total,
    selectedSignatureId,
    selectedSignature,
    authorizationLoading,
    authorizations,
    setActiveTab,
    setFilterValue,
    handleSearch,
    handleReset,
    handleSelectSignature,
    handleVerifySignature,
    handleToggleAuthorization,
  };
}
