import React, { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useRuntimeFeatureFlags } from '../hooks/useRuntimeFeatureFlags';
import './Tools.css';

const PAGE_SIZE = 12;

const ToolCard = ({ id, name, description, onClick, disabled, background }) => (
  <button
    type="button"
    onClick={onClick}
    disabled={disabled}
    className="tools-med-card"
    style={background ? { background } : undefined}
    data-testid={`tool-card-${id}`}
  >
    <div className="tools-med-card__name">{name}</div>
    <div className="tools-med-card__desc">{description}</div>
  </button>
);

const Tools = () => {
  const navigate = useNavigate();
  const { isAdmin, isSuperAdmin } = useAuth();
  const { flags } = useRuntimeFeatureFlags();
  const [page, setPage] = useState(1);

  const tools = useMemo(() => {
    const canSee = (flagKey) => isSuperAdmin() || flags?.[flagKey] !== false;
    const list = [];

    if (isAdmin() && canSee('tool_nas_visible')) {
      list.push({
        id: 'nas_browser',
        name: 'NAS 网盘',
        description: '浏览 NAS 共享目录中的文件夹和文件，仅管理员可见。',
        route: '/tools/nas-browser',
      });
    }

    if (isAdmin()) {
      list.push({
        id: 'collection_workbench',
        name: '采集工作台',
        description: '统一管理采集任务、失败分类、批量入库和过程日志。',
        route: '/tools/collection-workbench',
      });
    }

    list.push(
      {
        id: 'paper_download',
        name: '论文下载分析',
        description: '配置关键词、下载来源和数量上限，下载后自动加入本地论文。',
        route: '/tools/paper-download',
      },
      {
        id: 'paper_workspace',
        name: '论文工作台',
        description: '编辑论文、保存版本、提交查重、查看相似片段并导出报告。',
        route: '/tools/paper-workspace',
      },
      {
        id: 'patent_download',
        name: '专利下载分析',
        description: '配置关键词、数据源和数量上限，下载后自动加入本地专利。',
        route: '/tools/patent-download',
      }
    );

    if (canSee('tool_nhsa_visible')) {
      list.push({
        id: 'nhsa_code_search',
        name: '医保编码查询工具',
        description: '打开国家医保服务平台的医保编码查询页面（新窗口）。',
        href: 'https://code.nhsa.gov.cn/toSearch.html?sysflag=1004',
      });
    }

    if (canSee('tool_sh_tax_visible')) {
      list.push({
        id: 'shanghai_tax',
        name: '上海电子税务局',
        description: '打开上海电子税务局登录页面（新窗口）。',
        href: 'https://tpass.shanghai.chinatax.gov.cn:8443/#/login?response_type=code&client_id=d3f156f230415796834bed5e954ed4de&redirect_uri=https%3A%2F%2Fdppt.shanghai.chinatax.gov.cn%3A8443%2Fszzhzz%2FOauth2HandleServlet%3FcdPath%3DL2RlZGV1Y3Rpb24tdHlwZS1jaGVja2VkLWJ1c2luZXNzP3J1dWlkPTE3Njg1Mzg4ODUyMDUmb2F1dGgyc3RhdGU9N2Q4YTRlZDMzOWQyNGVhMWI3OTNlNzRjNDc5OWZlYzk%3D&state=1039c7dafc8d4ac69dcd1fac61121679&ruuid=1770379445455',
      });
    }

    if (canSee('tool_drug_admin_visible')) {
      list.push({
        id: 'drug_admin',
        name: '药监导航',
        description: '国家及各省药监局官网入口。',
        route: '/tools/drug-admin',
      });
    }

    if (canSee('tool_nmpa_visible')) {
      list.push({
        id: 'nmpa',
        name: 'NMPA 专用工具',
        description: '国家药监局相关专用工具入口。',
        route: '/tools/nmpa',
      });
    }

    for (let i = 4; i <= 48; i += 1) {
      list.push({
        id: `placeholder_${i}`,
        name: '待开放工具',
        description: '敬请期待',
        href: '',
      });
    }

    return list;
  }, [flags, isAdmin, isSuperAdmin]);

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
    window.alert('该工具尚未开放。');
  };

  return (
    <div className="tools-med-page">
      <div className="tools-med-head">
        <div className="medui-subtitle" data-testid="tools-page-indicator">
          第 <strong>{safePage}</strong> / {pageCount} 页
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button
            type="button"
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={safePage <= 1}
            data-testid="tools-prev-page"
            className="medui-btn medui-btn--secondary"
          >
            上一页
          </button>
          <button
            type="button"
            onClick={() => setPage((p) => Math.min(pageCount, p + 1))}
            disabled={safePage >= pageCount}
            data-testid="tools-next-page"
            className="medui-btn medui-btn--secondary"
          >
            下一页
          </button>
        </div>
      </div>

      <div className="tools-med-grid">
        {pageItems.map((t, idx) => (
          <ToolCard
            key={t.id}
            id={t.id}
            name={t.name}
            description={t.description}
            disabled={!(t.href || t.route)}
            onClick={() => openTool(t)}
            background={idx % 2 === 0 ? '#ffffff' : '#f9fcff'}
          />
        ))}
      </div>
    </div>
  );
};

export default Tools;
