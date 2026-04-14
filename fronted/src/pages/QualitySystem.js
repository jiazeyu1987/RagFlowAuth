import React from 'react';
import useQualitySystemPage from '../features/qualitySystem/useQualitySystemPage';

const TEXT = {
  pageTitle: '\u4f53\u7cfb\u6587\u4ef6\u5de5\u4f5c\u53f0',
  pageSummary: '\u8d28\u91cf\u90e8\u57fa\u4e8e capability \u8fdb\u5165\u5404\u6a21\u5757\uff0c\u5904\u7406\u6587\u63a7\u3001\u57f9\u8bad\u3001\u53d8\u66f4\u3001\u8bbe\u5907\u4e0e\u5ba1\u8ba1\u7b49\u4f53\u7cfb\u4e1a\u52a1\u3002',
  manageScope: '\u7ba1\u7406\u8303\u56f4',
  viewScope: '\u67e5\u770b\u8303\u56f4',
  noActions: '\u65e0\u53ef\u7528 action',
  enterModule: '\u8fdb\u5165\u8be5\u6a21\u5757',
  modulesTitle: '\u6a21\u5757\u63a5\u5165\u9762',
  modulesEmpty: '\u5f53\u524d\u8d26\u53f7\u6ca1\u6709\u53ef\u4f7f\u7528\u7684\u8d28\u91cf\u6a21\u5757\u6743\u9650\u3002',
  queueTitle: '\u8d28\u91cf\u5de5\u4f5c\u961f\u5217',
  queueLoading: '\u6b63\u5728\u52a0\u8f7d\u8d28\u91cf\u5de5\u4f5c\u961f\u5217...',
  queueEmpty: '\u5f53\u524d\u6ca1\u6709\u4e0e\u8d28\u91cf\u4f53\u7cfb\u8def\u7531\u76f8\u5173\u7684\u7ad9\u5185\u4fe1\u3002',
  openQueueItem: '\u6253\u5f00',
  statusUnread: '\u672a\u8bfb',
  statusRead: '\u5df2\u8bfb',
  resourceLabel: '\u8d44\u6e90',
  actionsLabel: '\u80fd\u529b',
  ownerLabel: 'Owner',
  pathLabel: '\u8def\u7531',
};

const pageStyle = {
  display: 'grid',
  gap: '16px',
};

const cardStyle = {
  background: '#ffffff',
  border: '1px solid #dbe2ea',
  borderRadius: '16px',
  padding: '18px',
  boxShadow: '0 10px 30px rgba(15, 23, 42, 0.06)',
};

const primaryButtonStyle = {
  border: '1px solid #0f766e',
  borderRadius: '10px',
  background: '#0f766e',
  color: '#ffffff',
  cursor: 'pointer',
  padding: '8px 12px',
};

const secondaryButtonStyle = {
  border: '1px solid #cbd5e1',
  borderRadius: '10px',
  background: '#ffffff',
  color: '#0f172a',
  cursor: 'pointer',
  padding: '8px 12px',
};

const pillStyle = (background, color) => ({
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  borderRadius: '999px',
  padding: '6px 10px',
  background,
  color,
  fontSize: '0.85rem',
  fontWeight: 700,
});

const moduleGridStyle = {
  display: 'grid',
  gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
  gap: '14px',
};

const detailGridStyle = {
  display: 'grid',
  gap: '6px',
  marginTop: '12px',
  color: '#475569',
  fontSize: '0.92rem',
};

const queueItemStyle = (unread) => ({
  border: unread ? '1px solid #99f6e4' : '1px solid #e2e8f0',
  borderRadius: '12px',
  padding: '14px',
  background: unread ? '#ecfeff' : '#ffffff',
});

const formatActions = (actions) => {
  if (!Array.isArray(actions) || actions.length === 0) {
    return TEXT.noActions;
  }
  return actions.join(', ');
};

export default function QualitySystem() {
  const {
    user,
    modules,
    canManageQualitySystem,
    queueLoading,
    queueError,
    queueItems,
    goToModule,
    openQueueItem,
  } = useQualitySystemPage();

  return (
    <div style={pageStyle} data-testid="quality-system-page">
      <section
        style={{
          ...cardStyle,
          background: 'linear-gradient(135deg, #f0fdfa 0%, #ecfeff 55%, #f8fafc 100%)',
          borderColor: '#99f6e4',
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
          <div>
            <h2 style={{ margin: 0, color: '#0f172a' }}>{TEXT.pageTitle}</h2>
            <p style={{ margin: '10px 0 0', color: '#334155', maxWidth: '720px', lineHeight: 1.6 }}>
              {TEXT.pageSummary}
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <span data-testid="quality-system-scope-pill" style={pillStyle('#ccfbf1', '#115e59')}>
              {canManageQualitySystem ? TEXT.manageScope : TEXT.viewScope}
            </span>
            <span style={pillStyle('#e2e8f0', '#334155')}>
              {String(user?.role || '-')}
            </span>
          </div>
        </div>
      </section>

      <section style={cardStyle}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
          <h3 style={{ margin: 0, color: '#0f172a' }}>{TEXT.modulesTitle}</h3>
          <span style={pillStyle('#dcfce7', '#166534')}>{`${modules.length} modules`}</span>
        </div>
        {modules.length === 0 ? (
          <div style={{ marginTop: '14px', color: '#64748b' }} data-testid="quality-system-modules-empty">
            {TEXT.modulesEmpty}
          </div>
        ) : (
          <div style={{ ...moduleGridStyle, marginTop: '14px' }}>
            {modules.map((module) => (
              <article
                key={module.key}
                data-testid={`quality-system-module-${module.key}`}
                style={{
                  border: '1px solid #dbe2ea',
                  borderRadius: '14px',
                  padding: '16px',
                  background: '#ffffff',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', flexWrap: 'wrap' }}>
                  <strong style={{ color: '#0f172a' }}>{module.title}</strong>
                  <span style={pillStyle('#f1f5f9', '#475569')}>{module.owner}</span>
                </div>
                <p style={{ margin: '10px 0 0', color: '#475569', lineHeight: 1.55 }}>
                  {module.summary}
                </p>
                <div style={detailGridStyle}>
                  <div><strong>{TEXT.pathLabel}:</strong> {module.path}</div>
                  <div><strong>{TEXT.resourceLabel}:</strong> {module.resource}</div>
                  <div><strong>{TEXT.actionsLabel}:</strong> {formatActions(module.actions)}</div>
                </div>
                <div style={{ marginTop: '14px' }}>
                  <button
                    type="button"
                    data-testid={`quality-system-open-${module.key}`}
                    onClick={() => goToModule(module.path)}
                    style={primaryButtonStyle}
                  >
                    {TEXT.enterModule}
                  </button>
                </div>
              </article>
            ))}
          </div>
        )}
      </section>

      <section style={cardStyle} data-testid="quality-system-queue-panel">
        <h3 style={{ margin: 0, color: '#0f172a' }}>{TEXT.queueTitle}</h3>
        {queueError ? (
          <div
            data-testid="quality-system-queue-error"
            style={{
              marginTop: '14px',
              borderRadius: '12px',
              background: '#fef2f2',
              color: '#991b1b',
              padding: '14px',
            }}
          >
            {queueError}
          </div>
        ) : null}
        {queueLoading ? (
          <div data-testid="quality-system-queue-loading" style={{ marginTop: '14px', color: '#475569' }}>
            {TEXT.queueLoading}
          </div>
        ) : queueItems.length === 0 ? (
          <div data-testid="quality-system-queue-empty" style={{ marginTop: '14px', color: '#64748b' }}>
            {TEXT.queueEmpty}
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '12px', marginTop: '14px' }}>
            {queueItems.map((item) => {
              const unread = String(item?.status || '') === 'unread';
              return (
                <div
                  key={item.inbox_id}
                  data-testid={`quality-system-queue-item-${item.inbox_id}`}
                  style={queueItemStyle(unread)}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ fontWeight: 700, color: '#0f172a' }}>
                        {String(item?.title || item?.event_type || '-')}
                      </div>
                      <div style={{ marginTop: '6px', color: '#475569' }}>
                        {String(item?.link_path || '/quality-system')}
                      </div>
                    </div>
                    <span style={pillStyle(unread ? '#cffafe' : '#f1f5f9', unread ? '#155e75' : '#475569')}>
                      {unread ? TEXT.statusUnread : TEXT.statusRead}
                    </span>
                  </div>
                  <div style={{ marginTop: '12px' }}>
                    <button
                      type="button"
                      data-testid={`quality-system-open-queue-item-${item.inbox_id}`}
                      onClick={() => openQueueItem(item)}
                      style={primaryButtonStyle}
                    >
                      {TEXT.openQueueItem}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
