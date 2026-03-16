import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ChatSafetyFlow from './ChatSafetyFlow';

function normalizeDisplayError(message, fallback) {
  const text = String(message || '').trim();
  if (!text) return fallback;
  return /[\u4e00-\u9fff]/.test(text) ? text : fallback;
}

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
  return (
    <div data-testid="chat-messages" className="chat-med-messages">
      {!selectedChatId ? (
        <div className="medui-empty">请先选择助手。</div>
      ) : !selectedSessionId ? (
        <div className="medui-empty">
          当前没有会话，请先新建一个会话。
          <div style={{ marginTop: 12 }}>
            <button
              onClick={onCreateSession}
              data-testid="chat-create-session-empty"
              type="button"
              className="medui-btn medui-btn--primary"
            >
              新建会话
            </button>
          </div>
        </div>
      ) : messages.length === 0 ? (
        <div className="medui-empty">开始新的对话吧。</div>
      ) : (
        messages.map((message, idx) => (
          <div
            key={idx}
            data-testid={`chat-message-${idx}-${message.role}`}
            className={`chat-med-msg-row ${message.role === 'user' ? 'is-user' : 'is-assistant'}`}
          >
            <div className={`chat-med-msg ${message.role === 'user' ? 'is-user' : 'is-assistant'}`}>
              {(() => {
                const raw = String(message.content ?? '');
                const assistantSegments = message.role === 'assistant' ? parseThinkSegments(raw) : [];
                const assistantVisible =
                  message.role === 'assistant'
                    ? assistantSegments
                        .filter((segment) => segment && segment.type === 'text')
                        .map((segment) => String(segment.text ?? ''))
                        .join('')
                    : '';

                const display = message.role === 'assistant' ? assistantVisible : raw;
                const markdownText = message.role === 'assistant' ? rewriteCitationLinks(display) : display;
                const citationIds = message.role === 'assistant' ? extractCitationIds(display) : [];
                const sources = Array.isArray(message.sources) ? message.sources : [];
                const uniqueCitationIds = (() => {
                  const output = [];
                  const seen = new Set();
                  for (const id of citationIds) {
                    const item = sources[id];
                    if (!item) continue;
                    const source = normalizeSource(item);
                    const key = String(source.title || source.docId || '').trim();
                    if (!key || seen.has(key)) continue;
                    seen.add(key);
                    output.push(id);
                  }
                  return output;
                })();

                const markdownComponents = {
                  p: ({ node, ...props }) => <p style={{ margin: '0 0 10px 0' }} {...props} />,
                  ul: ({ node, ...props }) => <ul style={{ margin: '0 0 10px 18px' }} {...props} />,
                  ol: ({ node, ...props }) => <ol style={{ margin: '0 0 10px 18px' }} {...props} />,
                  pre: ({ node, ...props }) => (
                    <pre
                      style={{
                        margin: '0 0 10px 0',
                        padding: '10px 12px',
                        background: message.role === 'user' ? 'rgba(255,255,255,0.16)' : '#17324a',
                        color: '#f4f8fd',
                        borderRadius: '10px',
                        overflowX: 'auto',
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
                              background: message.role === 'user' ? 'rgba(255,255,255,0.18)' : '#dce9f7',
                            }
                          : undefined
                      }
                      {...props}
                    >
                      {children}
                    </code>
                  ),
                  a: ({ node, href, children, ...props }) => {
                    const targetHref = String(href || '');
                    if (message.role === 'assistant' && targetHref.startsWith('#cid-')) {
                      const idRaw = targetHref.slice('#cid-'.length);
                      const id = Number(idRaw);
                      const item = Number.isFinite(id) ? sources[id] : null;
                      const source = item ? normalizeSource(item) : null;
                      const chunk = source?.chunk || '';
                      return (
                        <span
                          onClick={(event) => {
                            event.preventDefault?.();
                            event.stopPropagation?.();
                            onCitationClick(event, { id: Number.isFinite(id) ? id : -1, chunk });
                          }}
                          className="chat-med-citation-link"
                          title="点击查看片段"
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
                        style={{ color: message.role === 'user' ? '#f8fcff' : '#0d5ea6', textDecoration: 'underline' }}
                      >
                        {children}
                      </a>
                    );
                  },
                };

                return (
                  <>
                    {message.role === 'assistant' ? (
                      <>
                        {assistantSegments.map((segment, segIdx) => {
                          if (!segment || !segment.text) return null;
                          if (segment.type === 'think') {
                            return (
                              <div key={`think-${segIdx}`} className="chat-med-think">
                                {String(segment.text ?? '')}
                              </div>
                            );
                          }
                          const part = rewriteCitationLinks(String(segment.text ?? ''));
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

                    {message.role === 'assistant' ? <ChatSafetyFlow flow={message.safetyFlow} messageIndex={idx} /> : null}
                    {message.role === 'assistant' && uniqueCitationIds.length > 0 ? (
                      <div className="chat-med-source">
                        <div style={{ fontSize: '0.85rem', color: '#58738c', marginBottom: 6 }}>引用文件</div>
                        {uniqueCitationIds.map((id) => {
                          const item = sources[id];
                          const source = item ? normalizeSource(item) : null;
                          const canOpen = Boolean(source?.docId && source?.dataset);
                          return (
                            <div key={id} className="chat-med-source-item">
                              <div style={{ minWidth: 0, flex: 1 }}>
                                <div style={{ fontSize: '0.88rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                                  {source ? source.title : '未知文件'}
                                </div>
                              </div>
                              <div style={{ display: 'flex', gap: 8 }}>
                                <button
                                  disabled={!canOpen}
                                  onClick={() => openSourcePreview(item)}
                                  data-testid={`chat-source-view-${id}`}
                                  type="button"
                                  className="medui-btn medui-btn--secondary"
                                  style={{ height: 32, padding: '0 10px' }}
                                >
                                  查看
                                </button>
                                {canDownloadFiles ? (
                                  <button
                                    disabled={!canOpen}
                                    onClick={() => {
                                      downloadSource(item).catch((error) => setError(normalizeDisplayError(error?.message, '下载失败')));
                                    }}
                                    type="button"
                                    className="medui-btn medui-btn--primary"
                                    style={{ height: 32, padding: '0 10px' }}
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
