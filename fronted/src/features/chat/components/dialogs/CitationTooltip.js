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
      className="chat-med-tooltip"
      style={{
        left: Math.min(Math.max(10, (citationHover.x || 0) - 220), window.innerWidth - 450),
        top: Math.min(Math.max(10, (citationHover.y || 0) - 10), window.innerHeight - 300),
      }}
    >
      <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
        {citationHover.chunk}
      </ReactMarkdown>
    </div>
  );
}
