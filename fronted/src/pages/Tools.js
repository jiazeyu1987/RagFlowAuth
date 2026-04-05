import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import drugAdminApi from '../features/drugAdmin/api';

const PAGE_SIZE = 12;
const MOBILE_BREAKPOINT = 768;

const toolPermissionKey = (tool) => String(tool?.permissionKey || tool?.id || '').trim();

const toProvinceToolId = (name) => (
  `drug_admin_${String(name || '')
    .trim()
    .replace(/[^0-9a-zA-Z\u4e00-\u9fa5]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'unknown'}`
);

const baseToolDefinitions = [
  {
    id: 'paper_download',
    name: '论文下载分析',
    description: '进入论文下载页面：配置关键词、下载源和上限，下载后可加入 [本地论文]。',
    route: '/tools/paper-download',
  },
  {
    id: 'patent_download',
    name: '专利下载分析',
    description: '进入专利下载页面：配置关键词、数据源和上限，下载后可加入 [本地专利]。',
    route: '/tools/patent-download',
  },
  {
    id: 'package_drawing',
    name: '包装图纸',
    description: '按型号查询包装图纸信息，支持通过 Excel 录入型号、条形码、产品参数和示意图。',
    route: '/tools/package-drawing',
  },
  {
    id: 'nhsa_code_search',
    name: '医保编码查询工具',
    description: '打开国家医保服务平台：医保编码查询（新窗口）。',
    href: 'https://code.nhsa.gov.cn/toSearch.html?sysflag=1004',
  },
  {
    id: 'shanghai_tax',
    name: '上海电子税务局',
    description: '打开上海电子税务局登录页面（新窗口）。',
    href: 'https://tpass.shanghai.chinatax.gov.cn:8443/#/login?response_type=code&client_id=d3f156f230415796834bed5e954ed4de&redirect_uri=https%3A%2F%2Fdppt.shanghai.chinatax.gov.cn%3A8443%2Fszzhzz%2FOauth2HandleServlet%3FcdPath%3DL2RlZGV1Y3Rpb24tdHlwZS1jaGVja2VkLWJ1c2luZXNzP3J1dWlkPTE3Njg1Mzg4ODUyMDUmb2F1dGgyc3RhdGU9N2Q4YTRlZDMzOWQyNGVhMWI3OTNlNzRjNDc5OWZlYzk%3D&state=1039c7dafc8d4ac69dcd1fac61121679&ruuid=1770379445455',
  },
  {
    id: 'drug_admin',
    name: '药监导航',
    description: '进入省级与国家药监官网导航页，可进一步查看各地真实入口。',
    route: '/tools/drug-admin',
  },
  {
    id: 'nmpa',
    name: 'NMPA',
    description: '国家药监局器审中心。',
    route: '/tools/nmpa',
  },
];

const buildProvinceTools = (provinces) => (
  (Array.isArray(provinces) ? provinces : [])
    .map((province) => {
      const name = String(province?.name || '').trim();
      const urls = Array.isArray(province?.urls)
        ? province.urls.map((url) => String(url || '').trim()).filter(Boolean)
        : [];
      if (!name || urls.length === 0) return null;
      return {
        id: toProvinceToolId(name),
        permissionKey: 'drug_admin',
        name: `${name}药监入口`,
        description: `打开 ${name} 药监相关官网入口（新窗口）。`,
        href: urls[0],
      };
    })
    .filter(Boolean)
);

const ToolCard = ({ id, name, description, onClick, disabled, background, isMobile }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    style={{
      textAlign: 'left',
      padding: isMobile ? '16px' : '21px',
      borderRadius: '18px',
      border: '1px solid #e5e7eb',
      background: disabled ? '#f3f4f6' : (background || 'white'),
      cursor: disabled ? 'not-allowed' : 'pointer',
      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      transition: 'transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease',
      minHeight: isMobile ? 'auto' : '210px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
    }}
    onMouseEnter={(e) => {
      if (disabled || isMobile) return;
      e.currentTarget.style.transform = 'translateY(-1px)';
      e.currentTarget.style.boxShadow = '0 6px 18px rgba(0,0,0,0.08)';
      e.currentTarget.style.borderColor = '#c7d2fe';
    }}
    onMouseLeave={(e) => {
      if (disabled || isMobile) return;
      e.currentTarget.style.transform = 'translateY(0px)';
      e.currentTarget.style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)';
      e.currentTarget.style.borderColor = '#e5e7eb';
    }}
    data-testid={`tool-card-${id}`}
  >
    <div
      style={{
        fontSize: isMobile ? '1.2rem' : '1.5rem',
        fontWeight: 900,
        color: disabled ? '#6b7280' : '#111827',
        lineHeight: 1.2,
        minHeight: isMobile ? 'auto' : '40%',
        display: '-webkit-box',
        WebkitBoxOrient: 'vertical',
        WebkitLineClamp: 2,
        overflow: 'hidden',
      }}
    >
      {name}
    </div>
    <div
      style={{
        marginTop: '12px',
        fontSize: isMobile ? '0.95rem' : '1.05rem',
        color: '#4b5563',
        lineHeight: 1.55,
        minHeight: isMobile ? 'auto' : '50%',
        display: '-webkit-box',
        WebkitBoxOrient: 'vertical',
        WebkitLineClamp: 4,
        overflow: 'hidden',
      }}
    >
      {description}
    </div>
  </button>
);

const Tools = () => {
  const navigate = useNavigate();
  const { isAdmin, canAccessTool } = useAuth();
  const [page, setPage] = useState(1);
  const [provinceTools, setProvinceTools] = useState([]);
  const [provinceError, setProvinceError] = useState('');
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

  useEffect(() => {
    let active = true;

    const loadProvinceTools = async () => {
      try {
        const response = await drugAdminApi.listProvinces();
        if (!active) return;
        setProvinceTools(buildProvinceTools(response?.provinces));
        setProvinceError('');
      } catch (error) {
        if (!active) return;
        setProvinceTools([]);
        setProvinceError(error?.message || '药监入口加载失败');
      }
    };

    loadProvinceTools();
    return () => {
      active = false;
    };
  }, []);

  const tools = useMemo(() => {
    const list = [
      ...(isAdmin()
        ? [{
            id: 'nas_browser',
            name: 'NAS 云盘',
            description: '浏览 NAS 共享中的文件夹和文件，仅管理员可见。',
            route: '/tools/nas-browser',
          }]
        : []),
      ...baseToolDefinitions,
      ...provinceTools,
    ];
    return list;
  }, [isAdmin, provinceTools]);

  const visibleTools = useMemo(
    () => tools.filter((tool) => canAccessTool(toolPermissionKey(tool))),
    [tools, canAccessTool]
  );

  const pageCount = Math.max(1, Math.ceil(visibleTools.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(1, page), pageCount);
  const start = (safePage - 1) * PAGE_SIZE;
  const pageItems = visibleTools.slice(start, start + PAGE_SIZE);

  const openTool = (tool) => {
    if (!canAccessTool(toolPermissionKey(tool))) return;
    if (tool.route) {
      navigate(tool.route);
      return;
    }
    if (tool.href) {
      window.open(tool.href, '_blank', 'noopener,noreferrer');
      return;
    }
  };

  return (
    <div
      style={{ padding: isMobile ? '12px' : '20px', width: '100%', boxSizing: 'border-box' }}
      data-testid="tools-page"
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: isMobile ? 'stretch' : 'baseline',
          flexDirection: isMobile ? 'column' : 'row',
          gap: '12px',
        }}
      >
        <div
          style={{
            display: 'flex',
            gap: '10px',
            alignItems: isMobile ? 'stretch' : 'center',
            flexDirection: isMobile ? 'column' : 'row',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={safePage <= 1}
            data-testid="tools-prev-page"
            style={{
              padding: '8px 12px',
              borderRadius: '10px',
              border: '1px solid #e5e7eb',
              background: safePage <= 1 ? '#f3f4f6' : 'white',
              cursor: safePage <= 1 ? 'not-allowed' : 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            上一页
          </button>
          <div style={{ color: '#6b7280', fontSize: '0.9rem' }} data-testid="tools-page-indicator">
            第 <span style={{ color: '#111827', fontWeight: 700 }}>{safePage}</span> / {pageCount} 页
          </div>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            disabled={safePage >= pageCount}
            data-testid="tools-next-page"
            style={{
              padding: '8px 12px',
              borderRadius: '10px',
              border: '1px solid #e5e7eb',
              background: safePage >= pageCount ? '#f3f4f6' : 'white',
              cursor: safePage >= pageCount ? 'not-allowed' : 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            下一页
          </button>
        </div>
      </div>

      {provinceError ? (
        <div
          data-testid="tools-error"
          style={{ marginTop: '12px', padding: '10px 12px', background: '#fef2f2', color: '#991b1b', borderRadius: '10px' }}
        >
          {provinceError}
        </div>
      ) : null}

      <div
        data-testid="tools-grid"
        style={{
          marginTop: '16px',
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: isMobile ? '12px' : '20px',
        }}
      >
        {!pageItems.length ? (
          <div
            data-testid="tools-empty-state"
            style={{ gridColumn: '1 / -1', color: '#6b7280', padding: 8 }}
          >
            暂无可访问的实用工具
          </div>
        ) : null}
        {pageItems.map((tool, idx) => (
          <ToolCard
            key={tool.id}
            id={tool.id}
            name={tool.name}
            description={tool.description}
            disabled={!(tool.href || tool.route)}
            onClick={() => openTool(tool)}
            background={idx % 2 === 0 ? '#ffffff' : '#f8fafc'}
            isMobile={isMobile}
          />
        ))}
      </div>
    </div>
  );
};

export default Tools;
