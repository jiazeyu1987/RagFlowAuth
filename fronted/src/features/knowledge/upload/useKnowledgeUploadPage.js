import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuth } from '../../../hooks/useAuth';
import useKnowledgeUploadDatasets from './useKnowledgeUploadDatasets';
import useKnowledgeUploadExtensions from './useKnowledgeUploadExtensions';
import useKnowledgeUploadFiles from './useKnowledgeUploadFiles';

const MOBILE_BREAKPOINT = 768;

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

export default function useKnowledgeUploadPage() {
  const navigate = useNavigate();
  const { accessibleKbs, loading: authLoading, canViewKbConfig } = useAuth();
  const canManageExtensions = canViewKbConfig();
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const datasetsState = useKnowledgeUploadDatasets({
    accessibleKbs,
    authLoading,
    setError,
  });
  const {
    extensionSet,
    ...extensionsState
  } = useKnowledgeUploadExtensions({
    canManageExtensions,
  });
  const filesState = useKnowledgeUploadFiles({
    kbId: datasetsState.kbId,
    loadingExtensions: extensionsState.loadingExtensions,
    allowedExtensions: extensionsState.allowedExtensions,
    extensionSet,
    navigate,
    setError,
    setSuccess,
  });

  return {
    canManageExtensions,
    isMobile,
    error,
    success,
    ...datasetsState,
    ...extensionsState,
    ...filesState,
  };
}
