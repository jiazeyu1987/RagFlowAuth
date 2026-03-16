export const DEFAULT_PATENT_SOURCES = {
  uspto: { enabled: false, limit: 15 },
  google_patents: { enabled: true, limit: 30 },
};

export const PATENT_LAST_CONFIG_KEY = 'patent_download_last_config_v1';

export const PATENT_LOCAL_KB_REF = '[本地专利]';

export const PATENT_SOURCE_LABEL_MAP = {
  uspto: '美国专利局（USPTO）',
  google_patents: '谷歌专利',
};

export const PATENT_BOX_STYLE = {
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: '12px',
  padding: '14px',
  boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
};

const reasonLabelMap = {
  missing_pdf_url: '缺少 PDF 链接',
  download_failed: '下载失败',
};

const normalizeBackendErrorText = (value, fallback) => {
  const text = String(value || '').trim();
  if (!text) return fallback;
  if (/[\u4e00-\u9fff]/.test(text)) return text;
  return fallback;
};

export function humanizeSourceError(msg) {
  const text = String(msg || '').trim();
  if (!text) return '-';
  const lower = text.toLowerCase();

  if (lower.includes('method chat not supported yet')) {
    return '自动分析失败：当前模型端点不支持对话模式。';
  }
  if (text === 'no_results') return '该来源无结果';
  if (text === 'source_not_implemented') return '该来源尚未实现';
  if (text.startsWith('auto_analyze_failed:')) {
    return `自动分析失败：${text.slice('auto_analyze_failed:'.length).trim()}`;
  }
  if (text.startsWith('download_failed:')) {
    return `下载失败：${text.slice('download_failed:'.length).trim()}`;
  }
  if (text.startsWith('source_failed:')) {
    return `来源失败：${normalizeBackendErrorText(text.slice('source_failed:'.length).trim(), '请检查来源配置')}`;
  }
  return normalizeBackendErrorText(text, '来源异常，请检查配置后重试');
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
    return '自动分析失败：当前模型端点不支持对话模式。';
  }
  return normalizeBackendErrorText(text, '自动分析失败，请检查模型与网络配置');
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
        `${sourceLabelMap[key] || key}：跳过统计 - 关键词 ${skippedKeyword}，重复 ${skippedDuplicate}，停止 ${skippedStopped}`
      );
    }

    const failedReasons =
      stat?.failed_reasons && typeof stat.failed_reasons === 'object'
        ? stat.failed_reasons
        : {};
    Object.entries(failedReasons).forEach(([reason, count]) => {
      const n = Number(count || 0);
      if (n <= 0) return;
      lines.push(`${sourceLabelMap[key] || key}：失败原因 - ${reasonLabelMap[reason] || reason} ${n}`);
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
