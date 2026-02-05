import React, { useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize from 'rehype-sanitize';
import { ensureTablePreviewStyles } from './tablePreviewStyles';

export const isMarkdownFilename = (name) => {
  const s = String(name || '').toLowerCase();
  return s.endsWith('.md') || s.endsWith('.markdown');
};

export const MarkdownPreview = ({ content }) => {
  useEffect(() => {
    ensureTablePreviewStyles();
  }, []);

  return (
    <div
      style={{
        padding: '24px',
        backgroundColor: 'white',
        borderRadius: '8px',
        height: '70vh',
        overflow: 'auto',
        border: '1px solid #e5e7eb',
      }}
    >
      <div style={{ fontSize: '0.875rem', lineHeight: '1.6', color: '#1f2937' }} className="table-preview">
        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw, rehypeSanitize]}>
          {content || ''}
        </ReactMarkdown>
      </div>
    </div>
  );
};

