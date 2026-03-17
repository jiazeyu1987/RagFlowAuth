import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import authClient from '../api/authClient';
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
  const [stats, setStats] = useState({ pending: 0, approved: 0, rejected: 0, total: 0 });

  const capabilities = useMemo(
    () => ({
      canBrowse: can('ragflow_documents', 'view'),
      canViewKb: can('kb_documents', 'view'),
      canUploadKb: can('kb_documents', 'upload'),
      canReviewKb: can('kb_documents', 'review'),
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
        if (capabilities.canViewKb) {
          const data = await authClient.getStats();
          if (!cancelled) {
            setStats({
              pending: Number(data?.pending_documents || 0),
              approved: Number(data?.approved_documents || 0),
              rejected: Number(data?.rejected_documents || 0),
              total: Number(data?.total_documents || 0),
            });
          }
        }
      } catch (e) {
        if (!cancelled) setStatsError(e?.message || '加载统计信息失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [capabilities.canViewKb]);

  const cards = useMemo(
    () => [
      { key: 'pending', title: '待审核', value: stats.pending, color: '#f59e0b', show: capabilities.canReviewKb, onClick: () => navigate('/documents') },
      { key: 'approved', title: '已通过', value: stats.approved, color: '#10b981', show: capabilities.canViewKb, onClick: () => navigate('/documents') },
      { key: 'rejected', title: '已驳回', value: stats.rejected, color: '#ef4444', show: capabilities.canViewKb, onClick: () => navigate('/documents') },
      { key: 'total', title: '总文档数', value: stats.total, color: '#3b82f6', show: capabilities.canViewKb, onClick: () => navigate('/documents') },
    ].filter((card) => card.show),
    [capabilities.canReviewKb, capabilities.canViewKb, navigate, stats]
  );

  if (loading) {
    return <div data-testid="dashboard-loading">加载中...</div>;
  }

  return (
    <div data-testid="dashboard-page">
      <div style={{ marginBottom: '14px' }}>
        <h2 style={{ margin: 0, color: '#111827' }}>控制台</h2>
        <div style={{ marginTop: '6px', color: '#6b7280', wordBreak: 'break-word' }}>
          用户：{user?.username || '-'} | 角色：{user?.role || '-'}
        </div>
      </div>

      {statsError ? <div data-testid="dashboard-stats-error" style={{ color: '#b91c1c', marginBottom: '12px' }}>{statsError}</div> : null}

      {cards.length > 0 ? (
        <div style={cardGridStyle(isMobile)}>
          {cards.map((card) => (
            <button key={card.key} type="button" data-testid={`dashboard-card-${card.key}`} onClick={card.onClick} style={{ ...cardStyle, textAlign: 'left', cursor: 'pointer' }}>
              <div style={{ color: '#6b7280', fontWeight: 700 }}>{card.title}</div>
              <div style={{ marginTop: '8px', fontSize: '1.8rem', color: card.color, fontWeight: 900 }}>{card.value}</div>
            </button>
          ))}
        </div>
      ) : (
        <div style={{ ...cardStyle, color: '#6b7280' }} data-testid="dashboard-empty">当前角色暂无可展示的统计卡片。</div>
      )}

      <div style={{ ...cardStyle, marginTop: '14px' }}>
        <div style={{ marginBottom: '10px', fontWeight: 900, color: '#111827' }}>快捷操作</div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap', flexDirection: isMobile ? 'column' : 'row' }}>
          {capabilities.canBrowse ? <button type="button" data-testid="dashboard-quick-browser" onClick={() => navigate('/browser')} style={quickButtonStyle('#2563eb', isMobile)}>浏览文档</button> : null}
          {capabilities.canUploadKb ? <button type="button" data-testid="dashboard-quick-upload" onClick={() => navigate('/upload')} style={quickButtonStyle('#059669', isMobile)}>上传文档</button> : null}
          {capabilities.canViewKb ? <button type="button" data-testid="dashboard-quick-documents" onClick={() => navigate('/documents')} style={quickButtonStyle('#7c3aed', isMobile)}>查看文档</button> : null}
        </div>
      </div>
    </div>
  );
}
