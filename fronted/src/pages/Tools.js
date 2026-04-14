import React from 'react';
import useToolsPage from '../features/drugAdmin/useToolsPage';

const toProvinceToolId = (name) => (
  `drug_admin_${String(name || '')
    .trim()
    .replace(/[^0-9a-zA-Z\u4e00-\u9fa5]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'unknown'}`
);

const baseToolDefinitions = [
  {
    id: 'paper_download',
    name: 'Paper Download and Analysis',
    description: 'Open the paper download workspace to configure keywords, data sources, and limits. Downloaded files can be added to [Local Papers].',
    route: '/tools/paper-download',
  },
  {
    id: 'patent_download',
    name: 'Patent Download and Analysis',
    description: 'Open the patent download workspace to configure keywords, data sources, and limits. Downloaded files can be added to [Local Patents].',
    route: '/tools/patent-download',
  },
  {
    id: 'package_drawing',
    name: 'Packaging Drawing',
    description: 'Search packaging drawing details by model. Supports Excel import for model numbers, barcodes, product parameters, and reference images.',
    route: '/tools/package-drawing',
  },
  {
    id: 'nhsa_code_search',
    name: 'NHSA Code Search Tool',
    description: 'Open the National Healthcare Security service platform for medical insurance code lookup (new window).',
    href: 'https://code.nhsa.gov.cn/toSearch.html?sysflag=1004',
  },
  {
    id: 'shanghai_tax',
    name: 'Shanghai Electronic Tax Bureau',
    description: 'Open the Shanghai Electronic Tax Bureau login page (new window).',
    href: 'https://tpass.shanghai.chinatax.gov.cn:8443/#/login?response_type=code&client_id=d3f156f230415796834bed5e954ed4de&redirect_uri=https%3A%2F%2Fdppt.shanghai.chinatax.gov.cn%3A8443%2Fszzhzz%2FOauth2HandleServlet%3FcdPath%3DL2RlZGV1Y3Rpb24tdHlwZS1jaGVja2VkLWJ1c2luZXNzP3J1dWlkPTE3Njg1Mzg4ODUyMDUmb2F1dGgyc3RhdGU9N2Q4YTRlZDMzOWQyNGVhMWI3OTNlNzRjNDc5OWZlYzk%3D&state=1039c7dafc8d4ac69dcd1fac61121679&ruuid=1770379445455',
  },
  {
    id: 'drug_admin',
    name: 'Drug Administration Navigation',
    description: 'Open provincial and national drug administration portal entries to access official websites by region.',
    route: '/tools/drug-admin',
  },
  {
    id: 'nmpa',
    name: 'NMPA',
    description: 'National Medical Products Administration service portal.',
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
        name: `${name} Drug Administration Portal`,
        description: `Open the ${name} drug administration official portal (new window).`,
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
    onMouseEnter={(event) => {
      if (disabled || isMobile) return;
      event.currentTarget.style.transform = 'translateY(-1px)';
      event.currentTarget.style.boxShadow = '0 6px 18px rgba(0,0,0,0.08)';
      event.currentTarget.style.borderColor = '#c7d2fe';
    }}
    onMouseLeave={(event) => {
      if (disabled || isMobile) return;
      event.currentTarget.style.transform = 'translateY(0px)';
      event.currentTarget.style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)';
      event.currentTarget.style.borderColor = '#e5e7eb';
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
  const {
    isMobile,
    provinceError,
    pageItems,
    safePage,
    pageCount,
    canGoPrev,
    canGoNext,
    goPrevPage,
    goNextPage,
    openTool,
  } = useToolsPage({
    baseTools: baseToolDefinitions,
    buildProvinceTools,
  });

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
            onClick={goPrevPage}
            disabled={!canGoPrev}
            data-testid="tools-prev-page"
            style={{
              padding: '8px 12px',
              borderRadius: '10px',
              border: '1px solid #e5e7eb',
              background: canGoPrev ? 'white' : '#f3f4f6',
              cursor: canGoPrev ? 'pointer' : 'not-allowed',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            Previous Page
          </button>
          <div style={{ color: '#6b7280', fontSize: '0.9rem' }} data-testid="tools-page-indicator">
            Page <span style={{ color: '#111827', fontWeight: 700 }}>{safePage}</span> of {pageCount}
          </div>
          <button
            type="button"
            onClick={goNextPage}
            disabled={!canGoNext}
            data-testid="tools-next-page"
            style={{
              padding: '8px 12px',
              borderRadius: '10px',
              border: '1px solid #e5e7eb',
              background: canGoNext ? 'white' : '#f3f4f6',
              cursor: canGoNext ? 'pointer' : 'not-allowed',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            Next Page
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
            No accessible utility tools are available.
          </div>
        ) : null}
        {pageItems.map((tool, index) => (
          <ToolCard
            key={tool.id}
            id={tool.id}
            name={tool.name}
            description={tool.description}
            disabled={!(tool.href || tool.route)}
            onClick={() => openTool(tool)}
            background={index % 2 === 0 ? '#ffffff' : '#f8fafc'}
            isMobile={isMobile}
          />
        ))}
      </div>
    </div>
  );
};

export default Tools;
