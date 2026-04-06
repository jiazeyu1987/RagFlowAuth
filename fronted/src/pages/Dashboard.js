import React from 'react';
import useDashboardPage from '../features/operationApproval/useDashboardPage';

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
  const { user, isMobile, loading, statsError, cards, quickActions } = useDashboardPage();

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
          {quickActions.map((action) => (
            <button
              key={action.key}
              type="button"
              data-testid={`dashboard-quick-${action.key}`}
              onClick={action.onClick}
              style={quickButtonStyle(action.color, isMobile)}
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
