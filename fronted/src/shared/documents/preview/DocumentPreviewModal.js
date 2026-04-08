import React, { useCallback, useEffect, useState } from 'react';
import { useEscapeClose } from '../../hooks/useEscapeClose';
import { ensureTablePreviewStyles } from '../../preview/tablePreviewStyles';
import DocumentPreviewContent from './DocumentPreviewContent';
import useDocumentPreviewSession from './useDocumentPreviewSession';
import { ControlledPreviewBadge } from './watermarkOverlay';

const MOBILE_BREAKPOINT = 768;

export const DocumentPreviewModal = ({
  open,
  target,
  onClose,
  canDownloadFiles = false,
  documentApi,
}) => {
  if (!documentApi) {
    throw new Error('document_api_required');
  }

  const preventCopyInPreview = true;
  const [isMaximized, setIsMaximized] = useState(false);
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });

  const {
    loading,
    error,
    payload,
    effectiveName,
    objectUrl,
    previewWatermark,
    onlyOfficeWatermark,
    onlyOfficeServerUrl,
    onlyOfficeConfig,
    pdfPageImages,
    pdfRendering,
    pdfRenderingMessage,
    resetPreviewSession,
    openOriginalHtml,
  } = useDocumentPreviewSession({
    open,
    target,
    documentApi,
    canDownloadFiles,
  });

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  useEffect(() => {
    if (!open) setIsMaximized(false);
  }, [open]);

  const close = useCallback(() => {
    resetPreviewSession();
    setIsMaximized(false);
    onClose?.();
  }, [onClose, resetPreviewSession]);

  useEscapeClose(open, close);

  useEffect(() => {
    ensureTablePreviewStyles();
  }, []);

  const blockCopyInteraction = useCallback(
    (event) => {
      if (!preventCopyInPreview) return;
      event.preventDefault();
      event.stopPropagation();
    },
    [preventCopyInPreview]
  );

  useEffect(() => {
    if (!open || !preventCopyInPreview) return undefined;

    const onKeyDown = (event) => {
      const key = String(event?.key || '').toLowerCase();
      const withCtrlOrMeta = Boolean(event.ctrlKey || event.metaKey);
      const isCopyLike =
        withCtrlOrMeta && (key === 'c' || key === 'x' || key === 'a' || key === 's' || key === 'p');
      const isShiftInsert = Boolean(event.shiftKey) && key === 'insert';
      if (!isCopyLike && !isShiftInsert) return;
      event.preventDefault();
      event.stopPropagation();
    };

    window.addEventListener('keydown', onKeyDown, true);
    return () => window.removeEventListener('keydown', onKeyDown, true);
  }, [open, preventCopyInPreview]);

  if (!open) return null;

  const viewerHeight = isMobile ? '64vh' : '78vh';
  const activeWatermark = payload?.type === 'onlyoffice' ? onlyOfficeWatermark : previewWatermark;

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
        onClick={(event) => event.stopPropagation()}
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
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              flexShrink: 0,
              marginLeft: 'auto',
            }}
          >
            <ControlledPreviewBadge watermark={activeWatermark} />
            {payload?.type === 'onlyoffice' ? (
              <button
                type="button"
                onClick={() => setIsMaximized((value) => !value)}
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
              onMouseEnter={(event) => {
                event.currentTarget.style.color = '#111827';
              }}
              onMouseLeave={(event) => {
                event.currentTarget.style.color = '#6b7280';
              }}
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
          <DocumentPreviewContent
            loading={loading}
            error={error}
            payload={payload}
            objectUrl={objectUrl}
            viewerHeight={viewerHeight}
            previewWatermark={previewWatermark}
            onlyOfficeWatermark={onlyOfficeWatermark}
            onlyOfficeServerUrl={onlyOfficeServerUrl}
            onlyOfficeConfig={onlyOfficeConfig}
            effectiveName={effectiveName}
            target={target}
            canDownloadFiles={canDownloadFiles}
            pdfRendering={pdfRendering}
            pdfRenderingMessage={pdfRenderingMessage}
            pdfPageImages={pdfPageImages}
            openOriginalHtml={openOriginalHtml}
            isMobile={isMobile}
          />
        </div>
      </div>
    </div>
  );
};
