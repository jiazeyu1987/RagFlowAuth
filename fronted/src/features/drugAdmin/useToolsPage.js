import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import drugAdminApi from './api';

const DEFAULT_PAGE_SIZE = 12;
const MOBILE_BREAKPOINT = 768;
const DEFAULT_PROVINCE_LOAD_ERROR = '\u836f\u76d1\u5165\u53e3\u52a0\u8f7d\u5931\u8d25';

const ADMIN_ONLY_TOOL = {
  id: 'nas_browser',
  name: 'NAS \u4e91\u76d8',
  description: '\u6d4f\u89c8 NAS \u5171\u4eab\u4e2d\u7684\u6587\u4ef6\u5939\u548c\u6587\u4ef6\uff0c\u4ec5\u7ba1\u7406\u5458\u53ef\u89c1\u3002',
  route: '/tools/nas-browser',
};

const toolPermissionKey = (tool) => String(tool?.permissionKey || tool?.id || '').trim();

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

export default function useToolsPage({
  baseTools = [],
  buildProvinceTools,
  pageSize = DEFAULT_PAGE_SIZE,
  provinceLoadErrorMessage = DEFAULT_PROVINCE_LOAD_ERROR,
}) {
  const navigate = useNavigate();
  const { isAdmin, canAccessTool } = useAuth();
  const [page, setPage] = useState(1);
  const [provinceTools, setProvinceTools] = useState([]);
  const [provinceError, setProvinceError] = useState('');
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    let active = true;

    const loadProvinceTools = async () => {
      try {
        const response = await drugAdminApi.listProvinces();
        if (!active) return;
        const nextTools = buildProvinceTools?.(response?.provinces);
        setProvinceTools(Array.isArray(nextTools) ? nextTools : []);
        setProvinceError('');
      } catch (error) {
        if (!active) return;
        setProvinceTools([]);
        setProvinceError(error?.message || provinceLoadErrorMessage);
      }
    };

    loadProvinceTools();
    return () => {
      active = false;
    };
  }, [buildProvinceTools, provinceLoadErrorMessage]);

  const tools = useMemo(() => {
    if (isAdmin()) {
      return [ADMIN_ONLY_TOOL, ...baseTools, ...provinceTools];
    }
    return [...baseTools, ...provinceTools];
  }, [baseTools, isAdmin, provinceTools]);

  const visibleTools = useMemo(
    () => tools.filter((tool) => canAccessTool(toolPermissionKey(tool))),
    [canAccessTool, tools]
  );

  const pageCount = Math.max(1, Math.ceil(visibleTools.length / pageSize));
  const safePage = Math.min(Math.max(1, page), pageCount);
  const start = (safePage - 1) * pageSize;
  const pageItems = visibleTools.slice(start, start + pageSize);

  const goPrevPage = useCallback(() => {
    setPage((previous) => Math.max(1, previous - 1));
  }, []);

  const goNextPage = useCallback(() => {
    setPage((previous) => Math.min(pageCount, previous + 1));
  }, [pageCount]);

  const openTool = useCallback((tool) => {
    if (!canAccessTool(toolPermissionKey(tool))) return;
    if (tool?.route) {
      navigate(tool.route);
      return;
    }
    if (tool?.href) {
      window.open(tool.href, '_blank', 'noopener,noreferrer');
    }
  }, [canAccessTool, navigate]);

  return {
    isMobile,
    provinceError,
    visibleTools,
    pageItems,
    safePage,
    pageCount,
    canGoPrev: safePage > 1,
    canGoNext: safePage < pageCount,
    goPrevPage,
    goNextPage,
    openTool,
  };
}
