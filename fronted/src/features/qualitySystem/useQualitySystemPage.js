import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import operationApprovalApi from '../operationApproval/api';
import { useAuth } from '../../hooks/useAuth';
import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';
import {
  QUALITY_SYSTEM_MODULES,
  QUALITY_SYSTEM_ROOT_PATH,
} from './moduleCatalog';

const TEXT = {
  queueLoadError: '\u52a0\u8f7d\u8d28\u91cf\u5de5\u4f5c\u961f\u5217\u5931\u8d25',
};

const isQualitySystemQueueItem = (item) => {
  const linkPath = String(item?.link_path || '').trim();
  return linkPath.startsWith(QUALITY_SYSTEM_ROOT_PATH);
};

export default function useQualitySystemPage() {
  const navigate = useNavigate();
  const { can, isAuthorized, user } = useAuth();
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueError, setQueueError] = useState('');
  const [queueItems, setQueueItems] = useState([]);

  const canManageQualitySystem = typeof can === 'function'
    ? can('quality_system', 'manage')
    : false;

  const visibleModules = useMemo(() => {
    if (typeof isAuthorized !== 'function') return [];
    return QUALITY_SYSTEM_MODULES.filter((module) => {
      if (module.accessPermission) {
        return isAuthorized({ permission: module.accessPermission });
      }
      if (Array.isArray(module.accessAnyPermissions) && module.accessAnyPermissions.length > 0) {
        return isAuthorized({ anyPermissions: module.accessAnyPermissions });
      }
      return false;
    });
  }, [isAuthorized]);

  useEffect(() => {
    let cancelled = false;

    const loadQueue = async () => {
      setQueueLoading(true);
      setQueueError('');
      try {
        const response = await operationApprovalApi.listInbox({ limit: 20 });
        if (cancelled) return;
        setQueueItems((response.items || []).filter(isQualitySystemQueueItem));
      } catch (requestError) {
        if (cancelled) return;
        setQueueItems([]);
        setQueueError(mapUserFacingErrorMessage(requestError?.message, TEXT.queueLoadError));
      } finally {
        if (!cancelled) {
          setQueueLoading(false);
        }
      }
    };

    loadQueue();

    return () => {
      cancelled = true;
    };
  }, []);

  return {
    user,
    modules: visibleModules,
    canManageQualitySystem,
    queueLoading,
    queueError,
    queueItems,
    goToRoot: () => navigate(QUALITY_SYSTEM_ROOT_PATH),
    goToModule: (path) => navigate(path),
    openQueueItem: (item) => {
      const linkPath = String(item?.link_path || '').trim();
      navigate(linkPath || QUALITY_SYSTEM_ROOT_PATH);
    },
  };
}
