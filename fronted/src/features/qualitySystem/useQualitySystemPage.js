import { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import operationApprovalApi from '../operationApproval/api';
import { useAuth } from '../../hooks/useAuth';
import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';
import {
  findQualitySystemModuleByPath,
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

const isModuleQueueItem = (item, modulePath) => {
  const linkPath = String(item?.link_path || '').trim();
  return linkPath.startsWith(modulePath);
};

export default function useQualitySystemPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { can, user } = useAuth();
  const [queueLoading, setQueueLoading] = useState(true);
  const [queueError, setQueueError] = useState('');
  const [queueItems, setQueueItems] = useState([]);

  const selectedModule = findQualitySystemModuleByPath(location.pathname);
  const canManageQualitySystem = typeof can === 'function'
    ? can('quality_system', 'manage')
    : false;

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

  const visibleQueueItems = selectedModule
    ? queueItems.filter((item) => isModuleQueueItem(item, selectedModule.path))
    : queueItems;

  return {
    user,
    modules: QUALITY_SYSTEM_MODULES,
    selectedModule,
    canManageQualitySystem,
    queueLoading,
    queueError,
    queueItems: visibleQueueItems,
    goToRoot: () => navigate(QUALITY_SYSTEM_ROOT_PATH),
    goToModule: (path) => navigate(path),
    openQueueItem: (item) => {
      const linkPath = String(item?.link_path || '').trim();
      navigate(linkPath || QUALITY_SYSTEM_ROOT_PATH);
    },
  };
}
