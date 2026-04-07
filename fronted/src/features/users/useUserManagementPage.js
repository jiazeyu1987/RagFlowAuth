import { useUserManagement } from './hooks/useUserManagement';
import useMobileBreakpoint from '../../shared/hooks/useMobileBreakpoint';

const MOBILE_BREAKPOINT = 768;

export default function useUserManagementPage() {
  const management = useUserManagement();
  const isMobile = useMobileBreakpoint(MOBILE_BREAKPOINT);

  return {
    ...management,
    isMobile,
  };
}
