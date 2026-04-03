import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useEscapeClose } from '../../hooks/useEscapeClose';
import { ensureTablePreviewStyles } from '../../preview/tablePreviewStyles';
import { isMarkdownFilename, MarkdownPreview } from '../../preview/markdownPreview';
import { loadDocumentPreview } from '../../preview/ragflowPreviewManager';
import documentClient, { DOCUMENT_SOURCE } from '../documentClient';
import OnlyOfficeViewer from './OnlyOfficeViewer';
import { ControlledPreviewBadge, WatermarkedPreviewFrame } from './watermarkOverlay';
import {
  ONLYOFFICE_EXTENSIONS,
  base64ToBytes,
  detectDelimiter,
  getFileExtensionLower,
  isCsvFilename,
  nowMs,
  parseDelimited,
  previewTrace,
  rowsToHtmlTable,
} from './previewUtils';

const MOBILE_BREAKPOINT = 768;

export const DocumentPreviewModal = ({ open, target, onClose, canDownloadFiles = false }) => {
  const preventCopyInPreview = true;
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [payload, setPayload] = useState(null);
  const [effectiveName, setEffectiveName] = useState('');
  const [objectUrl, setObjectUrl] = useState('');
  const [previewWatermark, setPreviewWatermark] = useState(null);
  const [onlyOfficeWatermark, setOnlyOfficeWatermark] = useState(null);
  const [onlyOfficeServerUrl, setOnlyOfficeServerUrl] = useState('');
  const [onlyOfficeConfig, setOnlyOfficeConfig] = useState(null);
  const [pdfPageImages, setPdfPageImages] = useState([]);
  const [pdfRendering, setPdfRendering] = useState(false);
  const [pdfRenderingMessage, setPdfRenderingMessage] = useState('');
  const [isMaximized, setIsMaximized] = useState(false);
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const lastUrlRef = useRef('');

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const close = useCallback(() => {
    setPayload(null);
    setError('');
    setEffectiveName('');
    setOnlyOfficeServerUrl('');
    setOnlyOfficeConfig(null);
    setPreviewWatermark(null);
    setOnlyOfficeWatermark(null);
    setIsMaximized(false);
    onClose?.();
  }, [onClose]);

  useEscapeClose(open, close);

  useEffect(() => {
    ensureTablePreviewStyles();
  }, []);

  useEffect(() => {
    if (!open) return;
    if (!target?.docId || !target?.source) return;

    let cancelled = false;
    const t0 = nowMs();
    const traceContext = {
      source: target?.source,
      docId: target?.docId,
      dataset: target?.datasetName || target?.dataset,
      title: target?.filename || target?.title,
    };
    const run = async () => {
      previewTrace('open:start', traceContext);
      setLoading(true);
      setError('');
      setPayload(null);
      setPreviewWatermark(null);
      setOnlyOfficeWatermark(null);
      setOnlyOfficeServerUrl('');
      setOnlyOfficeConfig(null);
      setPdfPageImages([]);
      setPdfRendering(false);
      setPdfRenderingMessage('');
      setIsMaximized(false);

      try {
        const source = target.source;
        const docId = target.docId;
        const datasetName = target.datasetName || target.dataset;
        const sessionId = target.sessionId;
        const title = target.filename || target.title || `document_${docId}`;
        const ext = getFileExtensionLower(title);
        previewTrace('route:detect', { ...traceContext, ext, canDownloadFiles });

        if (
          (source === DOCUMENT_SOURCE.RAGFLOW || source === DOCUMENT_SOURCE.KNOWLEDGE) &&
          ONLYOFFICE_EXTENSIONS.has(ext)
        ) {
          const onlyOfficeStart = nowMs();
          previewTrace('onlyoffice:editor-config:start', traceContext);
          const onlyOffice = await documentClient.onlyofficeEditorConfig({
            source,
            docId,
            datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? datasetName : undefined,
            sessionId:
              source === DOCUMENT_SOURCE.PATENT || source === DOCUMENT_SOURCE.PAPER
                ? sessionId
                : undefined,
            filename: title,
          });
          if (cancelled) return;
          previewTrace('onlyoffice:editor-config:done', {
            ...traceContext,
            elapsedMs: Math.round(nowMs() - onlyOfficeStart),
            serverUrl: onlyOffice?.server_url,
          });
          setEffectiveName(String(onlyOffice?.filename || title || ''));
          setOnlyOfficeServerUrl(String(onlyOffice?.server_url || ''));
          setOnlyOfficeConfig(onlyOffice?.config || null);
          setOnlyOfficeWatermark(onlyOffice?.watermark || null);
          setPayload({ type: 'onlyoffice' });
          return;
        }

        previewTrace('manager:load:start', traceContext);
        const data = await loadDocumentPreview({
          docId,
          dataset: datasetName,
          title,
          getPreviewJson: async ({ docId: _id, dataset }) =>
            documentClient.preview({
              source,
              docId: _id,
              datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? dataset : undefined,
              sessionId:
                source === DOCUMENT_SOURCE.PATENT || source === DOCUMENT_SOURCE.PAPER
                  ? sessionId
                  : undefined,
            }),
          getDownloadBlob: canDownloadFiles
            ? async ({ docId: _id, dataset, filename }) =>
                documentClient.downloadBlob({
                  source,
                  docId: _id,
                  datasetName: source === DOCUMENT_SOURCE.RAGFLOW ? dataset : undefined,
                  sessionId:
                    source === DOCUMENT_SOURCE.PATENT || source === DOCUMENT_SOURCE.PAPER
                      ? sessionId
                      : undefined,
                  filename,
                })
            : undefined,
        });

        if (cancelled) return;
        previewTrace('manager:load:done', {
          ...traceContext,
          type: data?.type,
          elapsedMs: Math.round(nowMs() - t0),
        });

        const name = String(data?.filename || title || '');
        setEffectiveName(name);
        setPayload(data || null);
        setPreviewWatermark(data?.watermark || null);

        if (lastUrlRef.current) {
          try {
            window.URL.revokeObjectURL(lastUrlRef.current);
          } catch {
            // ignore
          }
          lastUrlRef.current = '';
          setObjectUrl('');
        }

        if (data?.type === 'pdf' && data?.content) {
          if (canDownloadFiles) {
            const blob = new Blob([base64ToBytes(data.content)], { type: 'application/pdf' });
            const url = window.URL.createObjectURL(blob);
            lastUrlRef.current = url;
            setObjectUrl(url);
          } else {
            const pdfStart = nowMs();
            setPdfRendering(true);
            setPdfRenderingMessage('PDF 预览加载中...');
            try {
              const pdfBytes = base64ToBytes(data.content);
              const pdfjsLib = await import('pdfjs-dist/webpack.mjs');
              const loadingTask = pdfjsLib.getDocument({ data: pdfBytes });
              const pdf = await loadingTask.promise;
              const total = Number(pdf.numPages) || 0;
              const pages = [];

              for (let i = 1; i <= total; i++) {
                if (cancelled) return;
                setPdfRenderingMessage(`PDF 预览加载中 (${i}/${total})...`);
                previewTrace('pdf:render:page:start', { ...traceContext, page: i, total });
                const page = await pdf.getPage(i);
                const viewport = page.getViewport({ scale: 1.4 });
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d', { alpha: false });
                if (!ctx) continue;
                canvas.width = Math.ceil(viewport.width);
                canvas.height = Math.ceil(viewport.height);
                await page.render({ canvasContext: ctx, viewport }).promise;
                pages.push(canvas.toDataURL('image/png'));
                previewTrace('pdf:render:page:done', { ...traceContext, page: i, total });
              }

              if (!cancelled) setPdfPageImages(pages);
              previewTrace('pdf:render:done', {
                ...traceContext,
                pages: pages.length,
                elapsedMs: Math.round(nowMs() - pdfStart),
              });
            } catch (pdfError) {
              if (!cancelled) setError(pdfError?.message || 'PDF 预览失败');
              previewTrace('pdf:render:failed', { ...traceContext, error: pdfError?.message || String(pdfError) });
            } finally {
              if (!cancelled) {
                setPdfRendering(false);
                setPdfRenderingMessage('');
              }
            }
          }
        } else if (data?.type === 'html' && data?.content) {
          const blob = new Blob([base64ToBytes(data.content)], { type: 'text/html; charset=utf-8' });
          const url = window.URL.createObjectURL(blob);
          lastUrlRef.current = url;
          setObjectUrl(url);
        } else if (data?.type === 'image' && data?.content) {
          const imageType = data?.image_type || 'png';
          const mime = `image/${imageType}`;
          const blob = new Blob([base64ToBytes(data.content)], { type: mime });
          const url = window.URL.createObjectURL(blob);
          lastUrlRef.current = url;
          setObjectUrl(url);
        }
      } catch (e) {
        if (cancelled) return;
        setError(e?.message || '预览失败');
        previewTrace('open:failed', { ...traceContext, elapsedMs: Math.round(nowMs() - t0), error: e?.message || String(e) });
      } finally {
        if (!cancelled) {
          setLoading(false);
          previewTrace('open:done', { ...traceContext, elapsedMs: Math.round(nowMs() - t0) });
        }
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [open, target?.source, target?.docId, target?.datasetName, target?.dataset, target?.sessionId, target?.filename, target?.title, canDownloadFiles]);

  useEffect(() => {
    if (!open) return;
    return () => {
      if (lastUrlRef.current) {
        try {
          window.URL.revokeObjectURL(lastUrlRef.current);
        } catch {
          // ignore
        }
        lastUrlRef.current = '';
      }
    };
  }, [open]);

  const blockCopyInteraction = useCallback((event) => {
    if (!preventCopyInPreview) return;
    event.preventDefault();
    event.stopPropagation();
  }, [preventCopyInPreview]);

  useEffect(() => {
    if (!open || !preventCopyInPreview) return undefined;

    const onKeyDown = (event) => {
      const key = String(event?.key || '').toLowerCase();
      const withCtrlOrMeta = Boolean(event.ctrlKey || event.metaKey);
      const isCopyLike = withCtrlOrMeta && (key === 'c' || key === 'x' || key === 'a' || key === 's' || key === 'p');
      const isShiftInsert = Boolean(event.shiftKey) && key === 'insert';
      if (!isCopyLike && !isShiftInsert) return;
      event.preventDefault();
      event.stopPropagation();
    };

    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, [open, preventCopyInPreview]);

  const excelRenderHint = useMemo(() => {
    if (payload?.type !== 'excel') return '';
    return '如果 Excel 中包含流程图或形状，表格模式可能无法完整显示；可点击“原样预览 (HTML)”查看。';
  }, [payload?.type]);

  const openOriginalHtml = useCallback(async () => {
    if (!target?.docId || !target?.source) return;
    try {
      setLoading(true);
      setError('');
      const data = await documentClient.preview({
        source: target.source,
        docId: target.docId,
        datasetName: target.source === DOCUMENT_SOURCE.RAGFLOW ? target.datasetName || target.dataset : undefined,
        sessionId:
          target.source === DOCUMENT_SOURCE.PATENT || target.source === DOCUMENT_SOURCE.PAPER
            ? target.sessionId
            : undefined,
        render: 'html',
      });
      if (data?.type !== 'html' || !data?.content) throw new Error(data?.message || '此文件类型不支持原样预览 (HTML)');

      const name = String(data?.filename || effectiveName || '');
      setEffectiveName(name);
      setPayload(data);
      setPreviewWatermark(data?.watermark || null);
      setOnlyOfficeServerUrl('');
      setOnlyOfficeConfig(null);
      setOnlyOfficeWatermark(null);
      setPdfPageImages([]);
      setPdfRendering(false);
      setPdfRenderingMessage('');

      if (lastUrlRef.current) {
        try {
          window.URL.revokeObjectURL(lastUrlRef.current);
        } catch {
          // ignore
        }
        lastUrlRef.current = '';
        setObjectUrl('');
      }
      const blob = new Blob([base64ToBytes(data.content)], { type: 'text/html; charset=utf-8' });
      const url = window.URL.createObjectURL(blob);
      lastUrlRef.current = url;
      setObjectUrl(url);
    } catch (e) {
      setError(e?.message || '预览失败');
    } finally {
      setLoading(false);
    }
  }, [target, effectiveName]);

  if (!open) return null;

  const viewerHeight = isMobile ? '64vh' : '78vh';
  const activeWatermark = payload?.type === 'onlyoffice' ? onlyOfficeWatermark : previewWatermark;
  const renderWithWatermark = (content, height = '100%') => (
    <WatermarkedPreviewFrame watermark={previewWatermark} height={height}>
      {content}
    </WatermarkedPreviewFrame>
  );

  return (
    <div
      onClick={close}
      data-testid="document-preview-modal"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        zIndex: 1100,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: isMaximized ? 0 : isMobile ? '8px' : '16px',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: 'white',
          borderRadius: isMaximized ? 0 : isMobile ? '14px' : '10px',
          width: isMaximized ? '100vw' : isMobile ? '100%' : '95vw',
          maxWidth: isMaximized ? '100vw' : isMobile ? '100%' : '1200px',
          height: isMaximized ? '100vh' : isMobile ? 'calc(100vh - 16px)' : '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1)',
        }}
      >
        <div
          style={{
            padding: isMobile ? '12px 14px' : '14px 18px',
            borderBottom: '1px solid #e5e7eb',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            gap: '10px',
            flexWrap: isMobile ? 'wrap' : 'nowrap',
          }}
        >
          <div
            style={{
              fontWeight: 700,
              fontSize: isMobile ? '0.98rem' : '1.05rem',
              color: '#111827',
              minWidth: 0,
              flex: 1,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: isMobile ? 'normal' : 'nowrap',
              wordBreak: 'break-word',
            }}
          >
            {effectiveName || target?.filename || target?.title || '文档预览'}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0, marginLeft: 'auto' }}>
            <ControlledPreviewBadge watermark={activeWatermark} />
            {payload?.type === 'onlyoffice' ? (
              <button
                type="button"
                onClick={() => setIsMaximized((v) => !v)}
                data-testid="document-preview-toggle-maximize"
                style={{
                  border: '1px solid #d1d5db',
                  borderRadius: '8px',
                  background: '#ffffff',
                  color: '#374151',
                  fontSize: '0.86rem',
                  padding: '6px 10px',
                  cursor: 'pointer',
                }}
              >
                {isMaximized ? '窗口化' : '最大化'}
              </button>
            ) : null}
            <button
              type="button"
              onClick={close}
              data-testid="document-preview-close"
              style={{
                background: 'transparent',
                border: 'none',
                fontSize: '1.4rem',
                cursor: 'pointer',
                color: '#6b7280',
                width: '36px',
                height: '36px',
                borderRadius: '8px',
              }}
              onMouseEnter={(e) => (e.currentTarget.style.color = '#111827')}
              onMouseLeave={(e) => (e.currentTarget.style.color = '#6b7280')}
              aria-label="close"
            >
              ×
            </button>
          </div>
        </div>

        <div
          onCopy={blockCopyInteraction}
          onCut={blockCopyInteraction}
          onPaste={blockCopyInteraction}
          onContextMenu={blockCopyInteraction}
          onDragStart={blockCopyInteraction}
          onSelectStart={blockCopyInteraction}
          style={{
            flex: 1,
            overflow: 'auto',
            padding: isMobile ? '12px' : '18px',
            userSelect: preventCopyInPreview ? 'none' : 'auto',
            WebkitUserSelect: preventCopyInPreview ? 'none' : 'auto',
            MozUserSelect: preventCopyInPreview ? 'none' : 'auto',
            msUserSelect: preventCopyInPreview ? 'none' : 'auto',
          }}
        >
          {loading ? (
            <div style={{ color: '#6b7280' }}>加载中...</div>
          ) : error ? (
            <div style={{ color: '#991b1b' }}>{error}</div>
          ) : payload ? (
            (() => {
              const p = payload;

              if (p.type === 'excel' && p.sheets) {
                const sheetNames = Object.keys(p.sheets || {});
                return (
                  renderWithWatermark(
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
                      <div style={{ flex: 1 }}>{excelRenderHint}</div>
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
                      <div key={sheetName} style={{ marginBottom: index < sheetNames.length - 1 ? '32px' : 0 }}>
                        {sheetNames.length > 1 && (
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
                        )}
                        <div style={{ overflowX: 'auto' }} dangerouslySetInnerHTML={{ __html: p.sheets[sheetName] }} />
                      </div>
                    ))}
                    </div>
                  )
                );
              }

              if (p.type === 'text') {
                const text = String(p.content || '');
                const name = String(p.filename || effectiveName || '');

                if (isCsvFilename(name)) {
                  const firstLine = text.split(/\r?\n/)[0] || '';
                  const delimiter = detectDelimiter(firstLine);
                  const rows = parseDelimited(text, delimiter);
                  const tableHtml = rowsToHtmlTable(rows);
                  return renderWithWatermark(<div className="table-preview" dangerouslySetInnerHTML={{ __html: tableHtml }} />);
                }

                if (isMarkdownFilename(name)) return renderWithWatermark(<MarkdownPreview content={text} />);
                return renderWithWatermark(<pre style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{text}</pre>);
              }

              if (p.type === 'docx') {
                return renderWithWatermark(
                  <div className="table-preview" style={{ padding: '16px', border: '1px solid #e5e7eb', borderRadius: '10px' }}>
                    <div
                      style={{ fontSize: '0.95rem', lineHeight: '1.65', color: '#111827' }}
                      dangerouslySetInnerHTML={{ __html: String(p.html || '') }}
                    />
                  </div>
                );
              }

              if (p.type === 'html' && objectUrl) {
                return renderWithWatermark(
                  <iframe title="html-preview" src={objectUrl} style={{ width: '100%', height: viewerHeight, border: '1px solid #e5e7eb', borderRadius: '10px' }} />,
                  viewerHeight
                );
              }

              if (p.type === 'onlyoffice' && onlyOfficeServerUrl && onlyOfficeConfig) {
                return (
                  <OnlyOfficeViewer
                    serverUrl={onlyOfficeServerUrl}
                    config={onlyOfficeConfig}
                    watermark={onlyOfficeWatermark}
                    height={viewerHeight}
                    traceContext={{ source: target?.source, docId: target?.docId, filename: effectiveName }}
                  />
                );
              }

              if (p.type === 'pdf' && objectUrl) {
                return renderWithWatermark(
                  <iframe title="pdf-preview" src={objectUrl} style={{ width: '100%', height: viewerHeight, border: '1px solid #e5e7eb', borderRadius: '10px' }} />,
                  viewerHeight
                );
              }

              if (p.type === 'pdf' && !canDownloadFiles) {
                if (pdfRendering) return renderWithWatermark(<div style={{ color: '#6b7280' }}>{pdfRenderingMessage || 'PDF 预览加载中...'}</div>, viewerHeight);
                if (pdfPageImages.length > 0) {
                  return renderWithWatermark(
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                      <div style={{ color: '#6b7280', fontSize: '0.88rem' }}>仅预览，不可下载或打印。</div>
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
                return renderWithWatermark(<div style={{ color: '#6b7280' }}>PDF 预览不可用</div>, viewerHeight);
              }

              if (p.type === 'image' && objectUrl) {
                return renderWithWatermark(
                  <div style={{ textAlign: 'center' }}>
                    <img alt={effectiveName || 'image'} src={objectUrl} style={{ maxWidth: '100%', maxHeight: viewerHeight, borderRadius: '10px' }} />
                  </div>,
                  viewerHeight
                );
              }

              return renderWithWatermark(<div style={{ color: '#6b7280' }}>{p.message || '暂不支持预览，请下载后查看。'}</div>);
            })()
          ) : (
            <div style={{ color: '#6b7280' }}>暂无内容</div>
          )}
        </div>
      </div>
    </div>
  );
};
