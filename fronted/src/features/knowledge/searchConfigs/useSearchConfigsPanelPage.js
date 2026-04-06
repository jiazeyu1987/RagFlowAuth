import { useCallback, useEffect, useState } from 'react';

import useSearchConfigsPanel from './useSearchConfigsPanel';

const MOBILE_BREAKPOINT = 768;

export default function useSearchConfigsPanelPage() {
  const panel = useSearchConfigsPanel();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleCreateModeChange = useCallback(
    (mode) => {
      panel.setCreateMode(mode);
      if (mode === 'blank') {
        panel.setCreateFromId('');
        panel.setCreateJsonText('{}');
      }
    },
    [panel]
  );

  const handleCreateSourceChange = useCallback(
    (configId) => {
      panel.setCreateFromId(configId);
      panel.syncCreateJsonFromCopy(configId);
    },
    [panel]
  );

  return {
    ...panel,
    isMobile,
    handleCreateModeChange,
    handleCreateSourceChange,
  };
}
