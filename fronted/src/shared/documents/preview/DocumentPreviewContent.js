import React from 'react';
import { isMarkdownFilename, MarkdownPreview } from '../../preview/markdownPreview';
import OnlyOfficeViewer from './OnlyOfficeViewer';
import { WatermarkedPreviewFrame } from './watermarkOverlay';
import {
  detectDelimiter,
  isCsvFilename,
  parseDelimited,
  rowsToHtmlTable,
} from './previewUtils';

const renderWithWatermark = (watermark, content, height = '100%') => (
  <WatermarkedPreviewFrame watermark={watermark} height={height}>
    {content}
  </WatermarkedPreviewFrame>
);

export default function DocumentPreviewContent({
  loading,
  error,
  payload,
  objectUrl,
  viewerHeight,
  previewWatermark,
  onlyOfficeWatermark,
  onlyOfficeServerUrl,
  onlyOfficeConfig,
  effectiveName,
  target,
  canDownloadFiles,
  pdfRendering,
  pdfRenderingMessage,
  pdfPageImages,
  openOriginalHtml,
  isMobile,
}) {
  if (loading) return <div style={{ color: '#6b7280' }}>加载中...</div>;
  if (error) return <div style={{ color: '#991b1b' }}>{error}</div>;
  if (!payload) return <div style={{ color: '#6b7280' }}>暂无内容</div>;

  if (payload.type === 'excel' && payload.sheets) {
    const sheetNames = Object.keys(payload.sheets || {});
    return renderWithWatermark(
      previewWatermark,
      <div className="table-preview" style={{ height: '100%', overflow: 'auto' }}>
        <div
          style={{
            display: 'flex',
            alignItems: isMobile ? 'stretch' : 'center',
            flexDirection: isMobile ? 'column' : 'row',
            gap: '10px',
            padding: '10px 12px',
            backgroundColor: '#eff6ff',
            border: '1px solid #bfdbfe',
            borderRadius: '10px',
            color: '#1e3a8a',
            fontSize: '0.95rem',
            marginBottom: '16px',
          }}
        >
          <div style={{ flex: 1 }}>
            如果 Excel 中包含流程图或形状，表格模式可能无法完整显示；可点击“原样预览
            (HTML)”查看。
          </div>
          <button
            type="button"
            onClick={openOriginalHtml}
            style={{
              width: isMobile ? '100%' : 'auto',
              padding: '8px 12px',
              backgroundColor: '#3b82f6',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '0.9rem',
              whiteSpace: 'nowrap',
            }}
          >
            原样预览 (HTML)
          </button>
        </div>

        {sheetNames.map((sheetName, index) => (
          <div
            key={sheetName}
            style={{ marginBottom: index < sheetNames.length - 1 ? '32px' : 0 }}
          >
            {sheetNames.length > 1 ? (
              <h3
                style={{
                  fontSize: '1.05rem',
                  fontWeight: 800,
                  margin: '0 0 12px 0',
                  color: '#111827',
                  borderBottom: '2px solid #e5e7eb',
                  paddingBottom: '8px',
                }}
              >
                {sheetName}
              </h3>
            ) : null}
            <div
              style={{ overflowX: 'auto' }}
              dangerouslySetInnerHTML={{ __html: payload.sheets[sheetName] }}
            />
          </div>
        ))}
      </div>
    );
  }

  if (payload.type === 'text') {
    const text = String(payload.content || '');
    const name = String(payload.filename || effectiveName || '');

    if (isCsvFilename(name)) {
      const firstLine = text.split(/\r?\n/)[0] || '';
      const delimiter = detectDelimiter(firstLine);
      const rows = parseDelimited(text, delimiter);
      const tableHtml = rowsToHtmlTable(rows);
      return renderWithWatermark(
        previewWatermark,
        <div className="table-preview" dangerouslySetInnerHTML={{ __html: tableHtml }} />
      );
    }

    if (isMarkdownFilename(name)) {
      return renderWithWatermark(
        previewWatermark,
        <MarkdownPreview content={text} />
      );
    }

    return renderWithWatermark(
      previewWatermark,
      <pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{text}</pre>
    );
  }

  if (payload.type === 'docx') {
    return renderWithWatermark(
      previewWatermark,
      <div
        className="table-preview"
        style={{ padding: '16px', border: '1px solid #e5e7eb', borderRadius: '10px' }}
      >
        <div
          style={{ fontSize: '0.95rem', lineHeight: '1.65', color: '#111827' }}
          dangerouslySetInnerHTML={{ __html: String(payload.html || '') }}
        />
      </div>
    );
  }

  if (payload.type === 'html' && objectUrl) {
    return renderWithWatermark(
      previewWatermark,
      <iframe
        title="html-preview"
        src={objectUrl}
        style={{
          width: '100%',
          height: viewerHeight,
          border: '1px solid #e5e7eb',
          borderRadius: '10px',
        }}
      />,
      viewerHeight
    );
  }

  if (payload.type === 'onlyoffice' && onlyOfficeServerUrl && onlyOfficeConfig) {
    return (
      <OnlyOfficeViewer
        serverUrl={onlyOfficeServerUrl}
        config={onlyOfficeConfig}
        watermark={onlyOfficeWatermark}
        height={viewerHeight}
        traceContext={{
          source: target?.source,
          docId: target?.docId,
          filename: effectiveName,
        }}
      />
    );
  }

  if (payload.type === 'pdf' && objectUrl) {
    return renderWithWatermark(
      previewWatermark,
      <iframe
        title="pdf-preview"
        src={objectUrl}
        style={{
          width: '100%',
          height: viewerHeight,
          border: '1px solid #e5e7eb',
          borderRadius: '10px',
        }}
      />,
      viewerHeight
    );
  }

  if (payload.type === 'pdf' && !canDownloadFiles) {
    if (pdfRendering) {
      return renderWithWatermark(
        previewWatermark,
        <div style={{ color: '#6b7280' }}>
          {pdfRenderingMessage || 'PDF 预览加载中...'}
        </div>,
        viewerHeight
      );
    }

    if (pdfPageImages.length > 0) {
      return renderWithWatermark(
        previewWatermark,
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ color: '#6b7280', fontSize: '0.88rem' }}>
            仅预览，不可下载或打印。
          </div>
          {pdfPageImages.map((imgSrc, index) => (
            <img
              key={`pdf-page-${index + 1}`}
              alt={`pdf-page-${index + 1}`}
              src={imgSrc}
              style={{
                width: '100%',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                backgroundColor: '#ffffff',
              }}
            />
          ))}
        </div>,
        viewerHeight
      );
    }

    return renderWithWatermark(
      previewWatermark,
      <div style={{ color: '#6b7280' }}>PDF 预览不可用</div>,
      viewerHeight
    );
  }

  if (payload.type === 'image' && objectUrl) {
    return renderWithWatermark(
      previewWatermark,
      <div style={{ textAlign: 'center' }}>
        <img
          alt={effectiveName || 'image'}
          src={objectUrl}
          style={{ maxWidth: '100%', maxHeight: viewerHeight, borderRadius: '10px' }}
        />
      </div>,
      viewerHeight
    );
  }

  return renderWithWatermark(
    previewWatermark,
    <div style={{ color: '#6b7280' }}>
      {payload.message || '暂不支持预览，请下载后查看。'}
    </div>
  );
}
