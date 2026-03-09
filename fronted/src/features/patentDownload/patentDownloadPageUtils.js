export const DEFAULT_PATENT_SOURCES = {
  uspto: { enabled: false, limit: 15 },
  google_patents: { enabled: true, limit: 30 },
};

export const PATENT_LAST_CONFIG_KEY = 'patent_download_last_config_v1';

export const PATENT_LOCAL_KB_REF = '[鏈湴涓撳埄]';

export const PATENT_SOURCE_LABEL_MAP = {
  uspto: 'USPTO',
  google_patents: 'Google Patents',
};

export const PATENT_BOX_STYLE = {
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '14px',
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
};

const reasonLabelMap = {
  missing_pdf_url: 'missing PDF URL',
  download_failed: 'download failed',
};

export function humanizeSourceError(msg) {
  const text = String(msg || '').trim();
  if (!text) return '-';
  const lower = text.toLowerCase();

  if (lower.includes('method chat not supported yet')) {
    return 'Auto analysis failed: current LLM endpoint does not support chat.';
  }
  if (text === 'no_results') return 'No results from this source';
  if (text === 'source_not_implemented') return 'Source is not implemented';
  if (text.startsWith('auto_analyze_failed:')) {
    return `Auto analysis failed: ${text.slice('auto_analyze_failed:'.length).trim()}`;
  }
  if (text.startsWith('download_failed:')) {
    return `Download failed: ${text.slice('download_failed:'.length).trim()}`;
  }
  if (text.startsWith('source_failed:')) {
    return `Source failed: ${text.slice('source_failed:'.length).trim()}`;
  }
  return text;
}

export function stripHtml(value) {
  return String(value || '')
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

export function isAnalysisErrorText(value) {
  const text = String(value || '').trim();
  if (!text) return false;
  const lower = text.toLowerCase();
  return (
    text.startsWith('auto_analyze_failed:') ||
    lower.startsWith('**error**') ||
    lower.startsWith('error:') ||
    lower.includes('method chat not supported yet') ||
    lower.includes('llm_error_response')
  );
}

export function humanizeAnalysisErrorText(value) {
  const text = String(value || '').trim();
  if (!text) return '';
  if (text.toLowerCase().includes('method chat not supported yet')) {
    return 'Auto analysis failed: current LLM endpoint does not support chat.';
  }
  return text;
}

export function buildPatentFrontendLogs({
  sourceErrors,
  sourceStats,
  items,
  autoAnalyze,
  sourceLabelMap = PATENT_SOURCE_LABEL_MAP,
}) {
  const lines = [];

  Object.entries(sourceErrors || {}).forEach(([key, msg]) => {
    lines.push(`${sourceLabelMap[key] || key}: ${humanizeSourceError(msg)}`);
  });

  Object.entries(sourceStats || {}).forEach(([key, stat]) => {
    const skippedKeyword = Number(stat?.skipped_keyword || 0);
    const skippedDuplicate = Number(stat?.skipped_duplicate || 0);
    const skippedStopped = Number(stat?.skipped_stopped || 0);

    if (skippedKeyword > 0 || skippedDuplicate > 0 || skippedStopped > 0) {
      lines.push(
        `${sourceLabelMap[key] || key}: skipped - keyword ${skippedKeyword}, duplicate ${skippedDuplicate}, stopped ${skippedStopped}`
      );
    }

    const failedReasons =
      stat?.failed_reasons && typeof stat.failed_reasons === 'object'
        ? stat.failed_reasons
        : {};
    Object.entries(failedReasons).forEach(([reason, count]) => {
      const n = Number(count || 0);
      if (n <= 0) return;
      lines.push(`${sourceLabelMap[key] || key}: failure reason - ${reasonLabelMap[reason] || reason} ${n}`);
    });
  });

  if (autoAnalyze) {
    (items || []).forEach((item) => {
      const text = String(item?.analysis_text || '').trim();
      if (!isAnalysisErrorText(text)) return;
      const title = stripHtml(item?.title || item?.filename || `patent_${item?.item_id || '-'}`);
      lines.push(`${title}: ${humanizeAnalysisErrorText(text)}`);
    });
  }

  return Array.from(new Set(lines));
}

export async function enrichPatentHistoryKeywords(rawList, manager, isDownloadedItemFn) {
  const list = Array.isArray(rawList) ? rawList : [];
  const needEnrich = list.some(
    (row) =>
      typeof row?.downloaded_count !== 'number' ||
      typeof row?.analyzed_count !== 'number' ||
      typeof row?.added_count !== 'number'
  );
  if (!needEnrich) return list;

  return Promise.all(
    list.map(async (row) => {
      const key = String(row?.history_key || '');
      if (!key) return row;
      try {
        const payload = await manager.getHistoryByKeyword(key);
        const rowItems = Array.isArray(payload?.items) ? payload.items : [];
        const downloadedCount = rowItems.filter((item) => isDownloadedItemFn(item)).length;
        const analyzedCount = rowItems.filter(
          (item) =>
            String(item?.analysis_text || '').trim() &&
            !isAnalysisErrorText(item?.analysis_text)
        ).length;
        const addedCount = rowItems.filter((item) => Boolean(item?.added_doc_id)).length;

        return {
          ...row,
          downloaded_count: downloadedCount,
          analyzed_count: analyzedCount,
          added_count: addedCount,
        };
      } catch (_) {
        return {
          ...row,
          downloaded_count: Number(row?.downloaded_count || 0),
          analyzed_count: Number(row?.analyzed_count || 0),
          added_count: Number(row?.added_count || 0),
        };
      }
    })
  );
}
