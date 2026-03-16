import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import authClient from '../api/authClient';
import { normalizeDisplayError } from '../shared/utils/displayError';

const CARD_TONES = {
  pending: { color: '#ad7a17', bg: '#fff7e7', border: '#f2d49f' },
  approved: { color: '#176a43', bg: '#f0faf4', border: '#b7e8cb' },
  rejected: { color: '#a53a3a', bg: '#fff4f4', border: '#f2c0c0' },
  total: { color: '#1f5f91', bg: '#edf6ff', border: '#c0daf2' },
};

const roleLabel = (user) => {
  if (user?.is_super_admin || String(user?.username || '').toLowerCase() === 'superadmin') return '超级管理员';
  const role = String(user?.role || '').trim().toLowerCase();
  if (role === 'admin') return '管理员';
  if (role === 'reviewer') return '审核员';
  if (role === 'operator') return '操作员';
  if (role === 'user') return '普通用户';
  return user?.role || '-';
};

export default function Dashboard() {
  const { user, can } = useAuth();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [statsError, setStatsError] = useState('');
  const [stats, setStats] = useState({
    pending: 0,
    approved: 0,
    rejected: 0,
    total: 0,
  });

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
        if (!cancelled) setStatsError(normalizeDisplayError(e?.message ?? e, '加载统计数据失败'));
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
    () =>
      [
        {
          key: 'pending',
          title: '待处理',
          value: stats.pending,
          show: capabilities.canReviewKb,
          onClick: () => navigate('/documents'),
        },
        {
          key: 'approved',
          title: '已通过',
          value: stats.approved,
          show: capabilities.canViewKb,
          onClick: () => navigate('/documents'),
        },
        {
          key: 'rejected',
          title: '已驳回',
          value: stats.rejected,
          show: capabilities.canViewKb,
          onClick: () => navigate('/documents'),
        },
        {
          key: 'total',
          title: '总数',
          value: stats.total,
          show: capabilities.canViewKb,
          onClick: () => navigate('/documents'),
        },
      ].filter((card) => card.show),
    [capabilities.canReviewKb, capabilities.canViewKb, navigate, stats]
  );

  if (loading) {
    return <div className="medui-empty" data-testid="dashboard-loading">加载中...</div>;
  }

  return (
    <div className="admin-med-page" data-testid="dashboard-page">
      <section className="medui-surface medui-card-pad">
        <div className="admin-med-head">
          <div>
            <h2 className="admin-med-title" style={{ margin: 0 }}>业务总览</h2>
            <div className="admin-med-inline-note" style={{ marginTop: 6 }}>
              用户：{user?.username || '-'} ｜ 角色：{roleLabel(user)}
            </div>
          </div>
        </div>
      </section>

      {statsError ? <div data-testid="dashboard-stats-error" className="admin-med-danger">{statsError}</div> : null}

      {cards.length > 0 ? (
        <section className="admin-med-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
          {cards.map((card) => {
            const tone = CARD_TONES[card.key] || CARD_TONES.total;
            return (
              <button
                key={card.key}
                type="button"
                data-testid={`dashboard-card-${card.key}`}
                onClick={card.onClick}
                className="medui-surface"
                style={{
                  textAlign: 'left',
                  cursor: 'pointer',
                  padding: 16,
                  borderColor: tone.border,
                  background: tone.bg,
                }}
              >
                <div style={{ color: '#5f768d', fontWeight: 700 }}>{card.title}</div>
                <div style={{ marginTop: 8, fontSize: '1.72rem', color: tone.color, fontWeight: 800 }}>{card.value}</div>
              </button>
            );
          })}
        </section>
      ) : (
        <div className="medui-surface medui-card-pad medui-empty" data-testid="dashboard-empty">
          当前角色暂无可展示的数据卡片。
        </div>
      )}

      <section className="medui-surface medui-card-pad">
        <div style={{ marginBottom: 10, fontWeight: 700, color: '#17324d' }}>快捷操作</div>
        <div className="admin-med-actions">
          {capabilities.canBrowse ? (
            <button type="button" data-testid="dashboard-quick-browser" onClick={() => navigate('/browser')} className="medui-btn medui-btn--secondary">
              浏览文档
            </button>
          ) : null}
          {capabilities.canUploadKb ? (
            <button type="button" data-testid="dashboard-quick-upload" onClick={() => navigate('/upload')} className="medui-btn medui-btn--success">
              上传文档
            </button>
          ) : null}
          {capabilities.canViewKb ? (
            <button type="button" data-testid="dashboard-quick-documents" onClick={() => navigate('/documents')} className="medui-btn medui-btn--primary">
              文档列表
            </button>
          ) : null}
        </div>
      </section>
    </div>
  );
}
