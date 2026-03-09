import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';

export default function CitationTooltip({ citationHover, onMouseLeave }) {
  if (!citationHover) return null;

  return (
    <div
      data-testid="chat-citation-tooltip"
      onMouseLeave={onMouseLeave}
      style={{
        position: 'fixed',
        left: Math.min(Math.max(10, (citationHover.x || 0) - 220), window.innerWidth - 450),
        top: Math.min(Math.max(10, (citationHover.y || 0) - 10), window.innerHeight - 300),
        width: '440px',
        maxWidth: 'calc(100vw - 20px)',
        maxHeight: '280px',
        overflow: 'auto',
        background: '#111827',
        color: '#f9fafb',
        border: '1px solid rgba(255,255,255,0.12)',
        borderRadius: '10px',
        padding: '10px 12px',
        zIndex: 900,
        boxShadow: '0 10px 25px rgba(0,0,0,0.25)',
        whiteSpace: 'pre-wrap',
        lineHeight: 1.45,
      }}
    >
      <style>{`
        .citation-tooltip-markdown table {
          border-collapse: collapse;
          width: 100%;
          font-size: 0.875rem;
        }
        .citation-tooltip-markdown th,
        .citation-tooltip-markdown td {
          border: 1px solid rgba(255,255,255,0.14);
          padding: 8px 10px;
          text-align: left;
          vertical-align: top;
        }
        .citation-tooltip-markdown th {
          background: rgba(255,255,255,0.08);
          font-weight: 700;
          color: #f9fafb;
        }
        .citation-tooltip-markdown tr:nth-child(even) {
          background: rgba(255,255,255,0.04);
        }
        .citation-tooltip-markdown a {
          color: #93c5fd;
        }
        .citation-tooltip-markdown p {
          margin: 0.35rem 0;
        }
        .citation-tooltip-markdown h1,
        .citation-tooltip-markdown h2,
        .citation-tooltip-markdown h3 {
          margin: 0.5rem 0 0.35rem 0;
        }
        .citation-tooltip-markdown code {
          background: rgba(255,255,255,0.08);
          padding: 0.1rem 0.25rem;
          border-radius: 4px;
        }
        .citation-tooltip-markdown pre {
          background: rgba(0,0,0,0.25);
          padding: 10px 12px;
          border-radius: 8px;
          overflow: auto;
        }
      `}</style>
      <div className="citation-tooltip-markdown">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
          {citationHover.chunk}
        </ReactMarkdown>
      </div>
    </div>
  );
}
