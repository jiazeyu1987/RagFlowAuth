import { useCallback, useEffect, useState } from 'react';
import authClient from '../api/authClient';

export const RUNTIME_VISIBILITY_DEFAULTS = {
  tool_nhsa_visible: true,
  tool_sh_tax_visible: true,
  tool_drug_admin_visible: true,
  tool_nmpa_visible: true,
  tool_nas_visible: true,
  page_data_security_test_visible: true,
  page_logs_visible: true,
  api_audit_events_visible: true,
  api_diagnostics_visible: true,
  api_admin_feature_flags_visible: true,
};

let cachedFlags = null;
let pendingRequest = null;

export const useRuntimeFeatureFlags = () => {
  const [loading, setLoading] = useState(true);
  const [flags, setFlags] = useState(cachedFlags || RUNTIME_VISIBILITY_DEFAULTS);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      if (!pendingRequest) {
        pendingRequest = authClient.getRuntimeFeatureFlags();
      }
      const payload = await pendingRequest;
      const merged = {
        ...RUNTIME_VISIBILITY_DEFAULTS,
        ...(payload && typeof payload === 'object' ? payload : {}),
      };
      cachedFlags = merged;
      setFlags(merged);
    } catch (_e) {
      setFlags(RUNTIME_VISIBILITY_DEFAULTS);
      cachedFlags = RUNTIME_VISIBILITY_DEFAULTS;
    } finally {
      pendingRequest = null;
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { loading, flags, reload: load };
};
