import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import operationApprovalApi from '../features/operationApproval/api';
import { useAuth } from '../hooks/useAuth';

const MOBILE_BREAKPOINT = 768;

const cardGridStyle = (isMobile) => ({
  display: 'grid',
  gridTemplateColumns: isMobile ? '1fr' : 'repeat(auto-fit, minmax(220px, 1fr))',
  gap: '14px',
});

const cardStyle = {
  background: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '16px',
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
};

const quickButtonStyle = (bg, isMobile) => ({
  padding: '10px 14px',
  borderRadius: '10px',
  border: 'none',
  background: bg,
  color: '#ffffff',
  cursor: 'pointer',
  fontWeight: 800,
  width: isMobile ? '100%' : 'auto',
});

export default function Dashboard() {
  const { user, can } = useAuth();
  const navigate = useNavigate();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [loading, setLoading] = useState(true);
  const [statsError, setStatsError] = useState('');
  const [stats, setStats] = useState({
    in_approval_count: 0,
    executed_count: 0,
    rejected_count: 0,
    execution_failed_count: 0,
  });

  const capabilities = useMemo(
    () => ({
      canBrowse: can('ragflow_documents', 'view'),
      canViewDocumentHistory: can('kb_documents', 'view'),
      canUploadKb: can('kb_documents', 'upload'),
    }),
    [can]
  );

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const run = async () => {
      setLoading(true);
      setStatsError('');
      try {
        const data = await operationApprovalApi.getStats();
        if (!cancelled) {
          setStats({
            in_approval_count: Number(data?.in_approval_count || 0),
            executed_count: Number(data?.executed_count || 0),
            rejected_count: Number(data?.rejected_count || 0),
            execution_failed_count: Number(data?.execution_failed_count || 0),
          });
        }
      } catch (error) {
        if (!cancelled) {
          setStatsError(error?.message || '加载审批统计失败');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, []);

  const cards = useMemo(
    () => [
      {
        key: 'in_approval',
        title: '审批中',
        value: stats.in_approval_count,
        color: '#2563eb',
        onClick: () => navigate('/approvals?status=in_approval'),
      },
      {
        key: 'executed',
        title: '已执行',
        value: stats.executed_count,
        color: '#15803d',
        onClick: () => navigate('/approvals?status=executed'),
      },
      {
        key: 'rejected',
        title: '已驳回',
        value: stats.rejected_count,
        color: '#dc2626',
        onClick: () => navigate('/approvals?status=rejected'),
      },
      {
        key: 'execution_failed',
        title: '执行失败',
        value: stats.execution_failed_count,
        color: '#b91c1c',
        onClick: () => navigate('/approvals?status=execution_failed'),
      },
    ],
    [navigate, stats]
  );

  if (loading) {
    return <div data-testid="dashboard-loading">加载中...</div>;
  }

  return (
    <div data-testid="dashboard-page">
      <div style={{ marginBottom: '14px' }}>
        <h2 style={{ margin: 0, color: '#111827' }}>控制台</h2>
        <div style={{ marginTop: '6px', color: '#6b7280', wordBreak: 'break-word' }}>
          用户：{user?.full_name || user?.username || '-'} | 角色：{user?.role || '-'}
        </div>
      </div>

      {statsError ? (
        <div data-testid="dashboard-stats-error" style={{ color: '#b91c1c', marginBottom: '12px' }}>
          {statsError}
        </div>
      ) : null}

      <div style={cardGridStyle(isMobile)}>
        {cards.map((card) => (
          <button
            key={card.key}
            type="button"
            data-testid={`dashboard-card-${card.key}`}
            onClick={card.onClick}
            style={{ ...cardStyle, textAlign: 'left', cursor: 'pointer' }}
          >
            <div style={{ color: '#6b7280', fontWeight: 700 }}>{card.title}</div>
            <div style={{ marginTop: '8px', fontSize: '1.8rem', color: card.color, fontWeight: 900 }}>
              {card.value}
            </div>
          </button>
        ))}
      </div>

      <div style={{ ...cardStyle, marginTop: '14px' }}>
        <div style={{ marginBottom: '10px', fontWeight: 900, color: '#111827' }}>快捷操作</div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', flexDirection: isMobile ? 'column' : 'row' }}>
          <button
            type="button"
            data-testid="dashboard-quick-approvals"
            onClick={() => navigate('/approvals')}
            style={quickButtonStyle('#2563eb', isMobile)}
          >
            查看审批
          </button>
          {capabilities.canUploadKb ? (
            <button
              type="button"
              data-testid="dashboard-quick-upload"
              onClick={() => navigate('/upload')}
              style={quickButtonStyle('#059669', isMobile)}
            >
              提交上传申请
            </button>
          ) : null}
          {capabilities.canViewDocumentHistory ? (
            <button
              type="button"
              data-testid="dashboard-quick-document-history"
              onClick={() => navigate('/document-history')}
              style={quickButtonStyle('#7c3aed', isMobile)}
            >
              查看文档记录
            </button>
          ) : null}
          {capabilities.canBrowse ? (
            <button
              type="button"
              data-testid="dashboard-quick-browser"
              onClick={() => navigate('/browser')}
              style={quickButtonStyle('#0f766e', isMobile)}
            >
              浏览文档
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
