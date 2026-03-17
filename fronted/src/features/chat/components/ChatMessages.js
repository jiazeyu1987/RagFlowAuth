import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

const MOBILE_BREAKPOINT = 768;

export default function ChatMessages({
  messagesEndRef,
  selectedChatId,
  selectedSessionId,
  messages,
  onCreateSession,
  parseThinkSegments,
  rewriteCitationLinks,
  extractCitationIds,
  normalizeSource,
  onCitationClick,
  openSourcePreview,
  downloadSource,
  canDownloadFiles,
  setError,
}) {
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

  return (
    <div data-testid="chat-messages" style={{ flex: 1, overflowY: 'auto', padding: isMobile ? '12px' : '16px' }}>
      {!selectedChatId ? (
        <div style={{ color: '#6b7280' }}>请先选择聊天助手</div>
      ) : !selectedSessionId ? (
        <div style={{ color: '#6b7280' }}>
          当前没有会话，请先新建一个会话。
          <div style={{ marginTop: '12px' }}>
            <button
              onClick={onCreateSession}
              data-testid="chat-create-session-empty"
              style={{
                padding: '10px 14px',
                borderRadius: '8px',
                border: 'none',
                backgroundColor: '#3b82f6',
                color: 'white',
                cursor: 'pointer',
                fontWeight: 600,
              }}
            >
              新建会话
            </button>
          </div>
        </div>
      ) : messages.length === 0 ? (
        <div style={{ color: '#6b7280' }}>开始新的对话...</div>
      ) : (
        messages.map((m, idx) => (
          <div
            key={idx}
            data-testid={`chat-message-${idx}-${m.role}`}
            style={{
              marginBottom: isMobile ? '10px' : '12px',
              display: 'flex',
              justifyContent: m.role === 'user' ? 'flex-end' : 'flex-start',
            }}
          >
            <div
              style={{
                maxWidth: isMobile ? (m.role === 'user' ? '88%' : '94%') : '75%',
                padding: isMobile ? '9px 11px' : '10px 12px',
                borderRadius: isMobile ? '12px' : '10px',
                backgroundColor: m.role === 'user' ? '#3b82f6' : '#f3f4f6',
                color: m.role === 'user' ? 'white' : '#111827',
                lineHeight: 1.55,
                overflowX: 'auto',
                boxSizing: 'border-box',
              }}
            >
              {(() => {
                const raw = String(m.content ?? '');
                const assistantSegments = m.role === 'assistant' ? parseThinkSegments(raw) : [];
                if (m.role === 'assistant' && raw.toLowerCase().includes('<think') && !assistantSegments.some((s) => s.type === 'think')) {
                  console.debug('[Chat:render] think tag present but no think segment parsed');
                }
                const assistantVisible =
                  m.role === 'assistant'
                    ? assistantSegments
                        .filter((s) => s && s.type === 'text')
                        .map((s) => String(s.text ?? ''))
                        .join('')
                    : '';

                const display = m.role === 'assistant' ? assistantVisible : raw;
                const markdownText = m.role === 'assistant' ? rewriteCitationLinks(display) : display;
                const citationIds = m.role === 'assistant' ? extractCitationIds(display) : [];
                const sources = Array.isArray(m.sources) ? m.sources : [];
                const uniqueCitationIds = (() => {
                  const out = [];
                  const seen = new Set();
                  for (const id of citationIds) {
                    const item = sources[id];
                    if (!item) continue;
                    const src = normalizeSource(item);
                    const key = String(src.title || src.docId || '').trim();
                    if (!key || seen.has(key)) continue;
                    seen.add(key);
                    out.push(id);
                  }
                  return out;
                })();
                const markdownComponents = {
                  p: ({ node, ...props }) => <p style={{ margin: '0 0 10px 0' }} {...props} />,
                  ul: ({ node, ...props }) => <ul style={{ margin: '0 0 10px 18px' }} {...props} />,
                  ol: ({ node, ...props }) => <ol style={{ margin: '0 0 10px 18px' }} {...props} />,
                  pre: ({ node, ...props }) => (
                    <pre
                      style={{
                        margin: '0 0 10px 0',
                        padding: isMobile ? '8px 10px' : '10px 12px',
                        background: m.role === 'user' ? 'rgba(255,255,255,0.12)' : '#111827',
                        color: m.role === 'user' ? 'white' : '#f9fafb',
                        borderRadius: '8px',
                        overflowX: 'auto',
                        fontSize: isMobile ? '0.85rem' : '0.92rem',
                      }}
                      {...props}
                    />
                  ),
                  code: ({ node, inline, className, children, ...props }) => (
                    <code
                      className={className}
                      style={
                        inline
                          ? {
                              padding: '0 6px',
                              borderRadius: '6px',
                              background: m.role === 'user' ? 'rgba(255,255,255,0.18)' : '#e5e7eb',
                            }
                          : undefined
                      }
                      {...props}
                    >
                      {children}
                    </code>
                  ),
                  a: ({ node, href, children, ...props }) => {
                    const h = String(href || '');
                    if (m.role === 'assistant' && h.startsWith('#cid-')) {
                      const idRaw = h.slice('#cid-'.length);
                      const id = Number(idRaw);
                      const item = Number.isFinite(id) ? sources[id] : null;
                      const src = item ? normalizeSource(item) : null;
                      const chunk = src?.chunk || '';
                      return (
                        <span
                          onClick={(e) => {
                            e.preventDefault?.();
                            e.stopPropagation?.();
                            onCitationClick(e, { id: Number.isFinite(id) ? id : -1, chunk });
                          }}
                          style={{
                            display: 'inline-block',
                            padding: '0 6px',
                            margin: '0 2px 4px 0',
                            borderRadius: '999px',
                            background: '#e5e7eb',
                            color: '#111827',
                            fontSize: '0.85em',
                            lineHeight: 1.6,
                            cursor: 'pointer',
                            userSelect: 'none',
                          }}
                          title="点击查看引用片段"
                        >
                          {children}
                        </span>
                      );
                    }
                    return (
                      <a
                        {...props}
                        href={href}
                        target="_blank"
                        rel="noreferrer"
                        style={{ color: m.role === 'user' ? 'white' : '#2563eb', textDecoration: 'underline' }}
                      >
                        {children}
                      </a>
                    );
                  },
                };

                return (
                  <>
                    {m.role === 'assistant' ? (
                      <>
                        {assistantSegments.map((seg, segIdx) => {
                          if (!seg || !seg.text) return null;
                          if (seg.type === 'think') {
                            return (
                              <div
                                key={`think-${segIdx}`}
                                style={{
                                  color: '#6b7280',
                                  fontSize: isMobile ? '0.82rem' : '0.9em',
                                  whiteSpace: 'pre-wrap',
                                  borderLeft: '3px solid #d1d5db',
                                  paddingLeft: '10px',
                                  margin: '0 0 10px 0',
                                }}
                              >
                                {String(seg.text ?? '')}
                              </div>
                            );
                          }
                          const part = rewriteCitationLinks(String(seg.text ?? ''));
                          if (!part) return null;
                          return (
                            <ReactMarkdown key={`text-${segIdx}`} components={markdownComponents} remarkPlugins={[remarkGfm]}>
                              {part}
                            </ReactMarkdown>
                          );
                        })}
                      </>
                    ) : (
                      <ReactMarkdown components={markdownComponents} remarkPlugins={[remarkGfm]}>
                        {markdownText}
                      </ReactMarkdown>
                    )}

                    {m.role === 'assistant' && uniqueCitationIds.length > 0 ? (
                      <div style={{ marginTop: '8px', borderTop: '1px solid #e5e7eb', paddingTop: '8px' }}>
                        <div style={{ fontSize: '0.85rem', color: '#6b7280', marginBottom: '6px' }}>引用文件</div>
                        {uniqueCitationIds.map((id) => {
                          const item = sources[id];
                          const src = item ? normalizeSource(item) : null;
                          const canOpen = Boolean(src?.docId && src?.dataset);
                          return (
                            <div
                              key={id}
                              style={{
                                display: 'flex',
                                flexDirection: isMobile ? 'column' : 'row',
                                alignItems: isMobile ? 'stretch' : 'center',
                                justifyContent: 'space-between',
                                gap: '10px',
                                padding: '8px',
                                borderRadius: '8px',
                                background: '#ffffff',
                                border: '1px solid #e5e7eb',
                                marginBottom: '6px',
                              }}
                            >
                              <div style={{ minWidth: 0, flex: 1 }}>
                                <div style={{ fontSize: '0.9rem', whiteSpace: isMobile ? 'normal' : 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', wordBreak: 'break-word' }}>
                                  {src ? src.title : '未知文件'}
                                </div>
                              </div>
                              <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', justifyContent: isMobile ? 'flex-end' : 'flex-start' }}>
                                <button
                                  disabled={!canOpen}
                                  onClick={() => openSourcePreview(item)}
                                  data-testid={`chat-source-view-${id}`}
                                  style={{
                                    padding: '6px 10px',
                                    borderRadius: '8px',
                                    border: '1px solid #d1d5db',
                                    background: canOpen ? '#ffffff' : '#f3f4f6',
                                    color: canOpen ? '#111827' : '#9ca3af',
                                    cursor: canOpen ? 'pointer' : 'not-allowed',
                                  }}
                                >
                                  查看
                                </button>
                                {canDownloadFiles ? (
                                  <button
                                    disabled={!canOpen}
                                    onClick={() => {
                                      downloadSource(item).catch((e) => setError(e?.message || '下载失败'));
                                    }}
                                    style={{
                                      padding: '6px 10px',
                                      borderRadius: '8px',
                                      border: 'none',
                                      background: canOpen ? '#3b82f6' : '#9ca3af',
                                      color: 'white',
                                      cursor: canOpen ? 'pointer' : 'not-allowed',
                                    }}
                                  >
                                    下载
                                  </button>
                                ) : null}
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : null}
                  </>
                );
              })()}
            </div>
          </div>
        ))
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}
