import React, { useEffect, useMemo, useRef, useState } from 'react';

import { nowMs, previewTrace } from './previewUtils';
import { WatermarkOverlay } from './watermarkOverlay';

export default function OnlyOfficeViewer({ serverUrl, config, traceContext, watermark, height = '78vh' }) {
  const containerId = useMemo(
    () => `onlyoffice-doc-editor-${Math.random().toString(36).slice(2)}`,
    []
  );
  const editorRef = useRef(null);
  const [viewerError, setViewerError] = useState('');
  const traceSource = traceContext?.source;
  const traceDocId = traceContext?.docId;
  const traceFilename = traceContext?.filename;

  useEffect(() => {
    if (!serverUrl || !config) return undefined;

    let disposed = false;
    const t0 = nowMs();
    const normalized = String(serverUrl || '').replace(/\/+$/, '');
    const scriptSrc = `${normalized}/web-apps/apps/api/documents/api.js`;
    const scriptId = `onlyoffice-docsapi-${normalized.replace(/[^a-zA-Z0-9]/g, '_')}`;
    let scriptEl = document.getElementById(scriptId);

    const initEditor = () => {
      if (disposed) return;
      if (!window.DocsAPI || typeof window.DocsAPI.DocEditor !== 'function') {
        setViewerError('ONLYOFFICE DocsAPI not ready');
        previewTrace('onlyoffice:init:not-ready', {
          source: traceSource,
          docId: traceDocId,
          filename: traceFilename,
          scriptSrc,
          elapsedMs: Math.round(nowMs() - t0),
        });
        return;
      }
      try {
        if (editorRef.current && typeof editorRef.current.destroyEditor === 'function') {
          editorRef.current.destroyEditor();
        }
        editorRef.current = new window.DocsAPI.DocEditor(containerId, config);
        setViewerError('');
        previewTrace('onlyoffice:init:done', {
          source: traceSource,
          docId: traceDocId,
          filename: traceFilename,
          elapsedMs: Math.round(nowMs() - t0),
        });
      } catch (e) {
        setViewerError(e?.message || 'ONLYOFFICE init failed');
        previewTrace('onlyoffice:init:failed', {
          source: traceSource,
          docId: traceDocId,
          filename: traceFilename,
          error: e?.message || String(e),
          elapsedMs: Math.round(nowMs() - t0),
        });
      }
    };

    const handleLoad = () => initEditor();
    const handleError = () => {
      setViewerError('Failed to load ONLYOFFICE script');
      previewTrace('onlyoffice:script:error', {
        source: traceSource,
        docId: traceDocId,
        filename: traceFilename,
        scriptSrc,
        elapsedMs: Math.round(nowMs() - t0),
      });
    };

    if (scriptEl) {
      scriptEl.addEventListener('load', handleLoad);
      scriptEl.addEventListener('error', handleError);
      if (window.DocsAPI && typeof window.DocsAPI.DocEditor === 'function') initEditor();
    } else {
      scriptEl = document.createElement('script');
      scriptEl.id = scriptId;
      scriptEl.src = scriptSrc;
      scriptEl.async = true;
      scriptEl.onload = handleLoad;
      scriptEl.onerror = handleError;
      document.body.appendChild(scriptEl);
      previewTrace('onlyoffice:script:append', {
        source: traceSource,
        docId: traceDocId,
        filename: traceFilename,
        scriptSrc,
      });
    }

    return () => {
      disposed = true;
      if (scriptEl) {
        scriptEl.removeEventListener('load', handleLoad);
        scriptEl.removeEventListener('error', handleError);
      }
      if (editorRef.current && typeof editorRef.current.destroyEditor === 'function') {
        try {
          editorRef.current.destroyEditor();
        } catch {
          // ignore
        }
      }
      editorRef.current = null;
    };
  }, [serverUrl, config, containerId, traceSource, traceDocId, traceFilename]);

  if (viewerError) return <div style={{ color: '#991b1b' }}>{viewerError}</div>;
  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        height,
        border: '1px solid #e5e7eb',
        borderRadius: '10px',
        overflow: 'hidden',
      }}
    >
      <div id={containerId} style={{ width: '100%', height: '100%' }} />
      <WatermarkOverlay watermark={watermark} />
    </div>
  );
}
