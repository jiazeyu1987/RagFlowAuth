import { useCallback, useEffect, useRef, useState } from 'react';
import { loadDocumentPreview } from '../../preview/ragflowPreviewManager';
import { DOCUMENT_SOURCE } from '../constants';
import {
  ONLYOFFICE_EXTENSIONS,
  base64ToBytes,
  getFileExtensionLower,
  nowMs,
  previewTrace,
} from './previewUtils';

const PREVIEW_FAILED_MESSAGE = '预览失败';
const PDF_LOADING_MESSAGE = 'PDF 预览加载中...';
const PDF_FAILED_MESSAGE = 'PDF 预览失败';
const HTML_RENDER_FAILED_MESSAGE = '此文件类型不支持原样预览 (HTML)';

const isSessionScopedSource = (source) =>
  source === DOCUMENT_SOURCE.PATENT || source === DOCUMENT_SOURCE.PAPER;

const resolveDatasetName = (target) => target?.datasetName || target?.dataset;

const resolveTitle = (target) =>
  target?.filename || target?.title || `document_${target?.docId}`;

const createPreviewRequest = (target, overrides = {}) => ({
  source: target.source,
  docId: target.docId,
  datasetName:
    target.source === DOCUMENT_SOURCE.RAGFLOW ? resolveDatasetName(target) : undefined,
  sessionId: isSessionScopedSource(target.source) ? target.sessionId : undefined,
  ...overrides,
});

const revokeObjectUrl = (url) => {
  if (!url || typeof window === 'undefined') return;
  try {
    window.URL.revokeObjectURL(url);
  } catch {
    // ignore
  }
};

export default function useDocumentPreviewSession({
  open,
  target,
  documentApi,
  canDownloadFiles,
}) {
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
  const lastUrlRef = useRef('');

  const clearObjectUrl = useCallback(() => {
    revokeObjectUrl(lastUrlRef.current);
    lastUrlRef.current = '';
    setObjectUrl('');
  }, []);

  const resetPreviewSession = useCallback(() => {
    setLoading(false);
    setError('');
    setPayload(null);
    setEffectiveName('');
    setPreviewWatermark(null);
    setOnlyOfficeWatermark(null);
    setOnlyOfficeServerUrl('');
    setOnlyOfficeConfig(null);
    setPdfPageImages([]);
    setPdfRendering(false);
    setPdfRenderingMessage('');
    clearObjectUrl();
  }, [clearObjectUrl]);

  const replaceObjectUrl = useCallback(
    (blob) => {
      clearObjectUrl();
      if (typeof window === 'undefined') return '';
      const nextUrl = window.URL.createObjectURL(blob);
      lastUrlRef.current = nextUrl;
      setObjectUrl(nextUrl);
      return nextUrl;
    },
    [clearObjectUrl]
  );

  useEffect(() => {
    if (open) return undefined;
    resetPreviewSession();
    return undefined;
  }, [open, resetPreviewSession]);

  useEffect(
    () => () => {
      revokeObjectUrl(lastUrlRef.current);
    },
    []
  );

  useEffect(() => {
    if (!open || !target?.docId || !target?.source) return undefined;

    let cancelled = false;
    const t0 = nowMs();
    const traceContext = {
      source: target.source,
      docId: target.docId,
      dataset: resolveDatasetName(target),
      title: resolveTitle(target),
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
      clearObjectUrl();

      try {
        const source = target.source;
        const docId = target.docId;
        const datasetName = resolveDatasetName(target);
        const title = resolveTitle(target);
        const ext = getFileExtensionLower(title);
        previewTrace('route:detect', { ...traceContext, ext, canDownloadFiles });

        if (
          (source === DOCUMENT_SOURCE.RAGFLOW || source === DOCUMENT_SOURCE.KNOWLEDGE) &&
          ONLYOFFICE_EXTENSIONS.has(ext)
        ) {
          const onlyOfficeStart = nowMs();
          previewTrace('onlyoffice:editor-config:start', traceContext);
          const onlyOffice = await documentApi.onlyofficeEditorConfig({
            ...createPreviewRequest(target),
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
          getPreviewJson: async ({ docId: previewDocId, dataset }) =>
            documentApi.preview(
              createPreviewRequest(target, {
                docId: previewDocId,
                datasetName:
                  target.source === DOCUMENT_SOURCE.RAGFLOW ? dataset : undefined,
              })
            ),
          getDownloadBlob: canDownloadFiles
            ? async ({ docId: previewDocId, dataset, filename }) =>
                documentApi.downloadBlob(
                  createPreviewRequest(target, {
                    docId: previewDocId,
                    datasetName:
                      target.source === DOCUMENT_SOURCE.RAGFLOW ? dataset : undefined,
                    filename,
                  })
                )
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

        if (data?.type === 'pdf' && data?.content) {
          if (canDownloadFiles) {
            replaceObjectUrl(
              new Blob([base64ToBytes(data.content)], { type: 'application/pdf' })
            );
          } else {
            const pdfStart = nowMs();
            setPdfRendering(true);
            setPdfRenderingMessage(PDF_LOADING_MESSAGE);
            try {
              const pdfBytes = base64ToBytes(data.content);
              const pdfjsLib = await import('pdfjs-dist/webpack.mjs');
              const loadingTask = pdfjsLib.getDocument({ data: pdfBytes });
              const pdf = await loadingTask.promise;
              const total = Number(pdf.numPages) || 0;
              const pages = [];

              for (let i = 1; i <= total; i += 1) {
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
              if (!cancelled) setError(pdfError?.message || PDF_FAILED_MESSAGE);
              previewTrace('pdf:render:failed', {
                ...traceContext,
                error: pdfError?.message || String(pdfError),
              });
            } finally {
              if (!cancelled) {
                setPdfRendering(false);
                setPdfRenderingMessage('');
              }
            }
          }
        } else if (data?.type === 'html' && data?.content) {
          replaceObjectUrl(
            new Blob([base64ToBytes(data.content)], {
              type: 'text/html; charset=utf-8',
            })
          );
        } else if (data?.type === 'image' && data?.content) {
          const imageType = data?.image_type || 'png';
          replaceObjectUrl(
            new Blob([base64ToBytes(data.content)], { type: `image/${imageType}` })
          );
        }
      } catch (requestError) {
        if (cancelled) return;
        setError(requestError?.message || PREVIEW_FAILED_MESSAGE);
        previewTrace('open:failed', {
          ...traceContext,
          elapsedMs: Math.round(nowMs() - t0),
          error: requestError?.message || String(requestError),
        });
      } finally {
        if (!cancelled) {
          setLoading(false);
          previewTrace('open:done', {
            ...traceContext,
            elapsedMs: Math.round(nowMs() - t0),
          });
        }
      }
    };

    run();
    return () => {
      cancelled = true;
    };
  }, [
    canDownloadFiles,
    clearObjectUrl,
    documentApi,
    open,
    replaceObjectUrl,
    target,
  ]);

  const openOriginalHtml = useCallback(async () => {
    if (!target?.docId || !target?.source) return;

    try {
      setLoading(true);
      setError('');
      const data = await documentApi.preview(
        createPreviewRequest(target, { render: 'html' })
      );
      if (data?.type !== 'html' || !data?.content) {
        throw new Error(data?.message || HTML_RENDER_FAILED_MESSAGE);
      }

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
      replaceObjectUrl(
        new Blob([base64ToBytes(data.content)], {
          type: 'text/html; charset=utf-8',
        })
      );
    } catch (requestError) {
      setError(requestError?.message || PREVIEW_FAILED_MESSAGE);
    } finally {
      setLoading(false);
    }
  }, [documentApi, effectiveName, replaceObjectUrl, target]);

  return {
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
  };
}
