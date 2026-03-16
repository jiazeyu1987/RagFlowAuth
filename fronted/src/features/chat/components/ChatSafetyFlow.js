import React from 'react';

const STATUS_META = {
  pending: {
    label: '待处理',
    color: '#6b7280',
    border: '#d1d5db',
    background: '#f9fafb',
  },
  running: {
    label: '执行中',
    color: '#1d4ed8',
    border: '#93c5fd',
    background: '#eff6ff',
  },
  success: {
    label: '已通过',
    color: '#166534',
    border: '#86efac',
    background: '#f0fdf4',
  },
  failed: {
    label: '已拦截',
    color: '#991b1b',
    border: '#fca5a5',
    background: '#fef2f2',
  },
  skipped: {
    label: '已跳过',
    color: '#6b7280',
    border: '#d1d5db',
    background: '#f9fafb',
  },
};

const getStatusMeta = (status) => STATUS_META[String(status || '').trim()] || STATUS_META.pending;

export default function ChatSafetyFlow({ flow, messageIndex }) {
  if (!flow || flow.visible === false) return null;
  const stages = Array.isArray(flow.stages) ? flow.stages : [];
  if (stages.length === 0) return null;

  const summary = String(flow.summary || '').trim() || '安全流程执行中。';

  return (
    <div data-testid={`chat-safety-flow-${messageIndex}`} className="chat-med-source">
      <div style={{ fontSize: '0.85rem', color: '#4b5563', marginBottom: '6px' }}>对话安全流程</div>
      <div
        style={{
          fontSize: '0.85rem',
          color: '#17324d',
          marginBottom: '8px',
          padding: '6px 8px',
          borderRadius: '8px',
          background: '#f4f9ff',
          border: '1px solid #d9e7f5',
        }}
      >
        {summary}
      </div>
      <div style={{ display: 'grid', gap: '6px' }}>
        {stages.map((stage) => {
          const meta = getStatusMeta(stage?.status);
          const title = String(stage?.label || '').trim() || '安全节点';
          const detail = String(stage?.detail || '').trim();
          return (
            <div
              key={String(stage?.key || title)}
              style={{
                border: `1px solid ${meta.border}`,
                background: meta.background,
                borderRadius: '8px',
                padding: '6px 8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                  <span
                    style={{
                      width: '8px',
                      height: '8px',
                      borderRadius: '999px',
                      background: meta.color,
                      flex: '0 0 8px',
                    }}
                  />
                  <span
                    style={{
                      color: '#111827',
                      fontSize: '0.86rem',
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}
                  >
                    {title}
                  </span>
                </div>
                <span style={{ color: meta.color, fontSize: '0.8rem', flexShrink: 0 }}>{meta.label}</span>
              </div>
              {detail ? (
                <div
                  style={{
                    marginTop: '4px',
                    fontSize: '0.8rem',
                    color: '#4b5563',
                    lineHeight: 1.45,
                    whiteSpace: 'pre-wrap',
                  }}
                >
                  {detail}
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
}
