import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

const PAGE_SIZE = 12;

const ToolCard = ({ id, name, description, onClick, disabled, background }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    style={{
      textAlign: 'left',
      padding: '21px 21px',
      borderRadius: '18px',
      border: '1px solid #e5e7eb',
      background: disabled ? '#f3f4f6' : (background || 'white'),
      cursor: disabled ? 'not-allowed' : 'pointer',
      boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
      transition: 'transform 0.12s ease, box-shadow 0.12s ease, border-color 0.12s ease',
      minHeight: '210px',
      display: 'flex',
      flexDirection: 'column',
      justifyContent: 'space-between',
    }}
    onMouseEnter={(e) => {
      if (disabled) return;
      e.currentTarget.style.transform = 'translateY(-1px)';
      e.currentTarget.style.boxShadow = '0 6px 18px rgba(0,0,0,0.08)';
      e.currentTarget.style.borderColor = '#c7d2fe';
    }}
    onMouseLeave={(e) => {
      if (disabled) return;
      e.currentTarget.style.transform = 'translateY(0px)';
      e.currentTarget.style.boxShadow = '0 1px 2px rgba(0,0,0,0.04)';
      e.currentTarget.style.borderColor = '#e5e7eb';
    }}
    data-testid={`tool-card-${id}`}
  >
    <div
      style={{
        fontSize: '1.5rem',
        fontWeight: 900,
        color: disabled ? '#6b7280' : '#111827',
        lineHeight: 1.2,
        minHeight: '40%',
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
        fontSize: '1.05rem',
        color: '#4b5563',
        lineHeight: 1.55,
        minHeight: '50%',
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
  const [page, setPage] = useState(1);

  const tools = useMemo(() => {
    const list = [
      {
        id: 'patent_download',
        name: '专利下载分析',
        description: '进入专利下载页面：配置关键词、数据源和上限，下载并添加到 [本地专利]。',
        route: '/tools/patent-download',
      },
      {
        id: 'nhsa_code_search',
        name: '医保编码查询工具',
        description: '打开国家医保服务平台：医保编码查询（新窗口）',
        href: 'https://code.nhsa.gov.cn/toSearch.html?sysflag=1004',
      },
      {
        id: 'shanghai_tax',
        name: '上海电子税务局',
        description: '打开上海电子税务局登录页（新窗口）',
        href: 'https://tpass.shanghai.chinatax.gov.cn:8443/#/login?response_type=code&client_id=d3f156f230415796834bed5e954ed4de&redirect_uri=https%3A%2F%2Fdppt.shanghai.chinatax.gov.cn%3A8443%2Fszzhzz%2FOauth2HandleServlet%3FcdPath%3DL2RlZGV1Y3Rpb24tdHlwZS1jaGVja2VkLWJ1c2luZXNzP3J1dWlkPTE3Njg1Mzg4ODUyMDUmb2F1dGgyc3RhdGU9N2Q4YTRlZDMzOWQyNGVhMWI3OTNlNzRjNDc5OWZlYzk%3D&state=1039c7dafc8d4ac69dcd1fac61121679&ruuid=1770379445455',
      },
    ];

    for (let i = 4; i <= 48; i++) {
      list.push({
        id: `tbd_${i}`,
        name: 'TBD',
        description: '敬请期待',
        href: '',
      });
    }

    return list;
  }, []);

  const pageCount = Math.max(1, Math.ceil(tools.length / PAGE_SIZE));
  const safePage = Math.min(Math.max(1, page), pageCount);
  const start = (safePage - 1) * PAGE_SIZE;
  const pageItems = tools.slice(start, start + PAGE_SIZE);

  const openTool = (tool) => {
    if (tool.route) {
      navigate(tool.route);
      return;
    }
    if (tool.href) {
      window.open(tool.href, '_blank', 'noopener,noreferrer');
      return;
    }
    window.alert('该工具尚未开放（TBD）。');
  };

  return (
    <div style={{ padding: '20px', width: '100%', boxSizing: 'border-box' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', gap: '12px' }}>
        <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={safePage <= 1}
            style={{
              padding: '8px 12px',
              borderRadius: '10px',
              border: '1px solid #e5e7eb',
              background: safePage <= 1 ? '#f3f4f6' : 'white',
              cursor: safePage <= 1 ? 'not-allowed' : 'pointer',
            }}
          >
            上一页
          </button>
          <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>
            第 <span style={{ color: '#111827', fontWeight: 700 }}>{safePage}</span> / {pageCount} 页
          </div>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            disabled={safePage >= pageCount}
            style={{
              padding: '8px 12px',
              borderRadius: '10px',
              border: '1px solid #e5e7eb',
              background: safePage >= pageCount ? '#f3f4f6' : 'white',
              cursor: safePage >= pageCount ? 'not-allowed' : 'pointer',
            }}
          >
            下一页
          </button>
        </div>
      </div>

      <div
        style={{
          marginTop: '16px',
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))',
          gap: '20px',
        }}
      >
        {pageItems.map((t, idx) => (
          <ToolCard
            key={t.id}
            id={t.id}
            name={t.name}
            description={t.description}
            disabled={!(t.href || t.route)}
            onClick={() => openTool(t)}
            background={idx % 2 === 0 ? '#ffffff' : '#f8fafc'}
          />
        ))}
      </div>
    </div>
  );
};

export default Tools;
