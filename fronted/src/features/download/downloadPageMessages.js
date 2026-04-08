export function buildDownloadMessages(localKbRef, messages) {
  const baseMessages = {
    keywordsError: '加载历史关键词失败',
    itemsError: '加载历史条目失败',
    startedInfo: '下载已开始，结果会持续返回。',
    downloadFailed: '下载失败',
    stopDoneInfo: '下载已停止',
    stopRequestedInfo: '已请求停止，等待当前条目处理完成。',
    stopFailed: '停止下载失败',
    progressFailed: '加载下载进度失败',
    noResultsError: '当前配置的数据源未返回可下载结果。',
    noDownloadedError: '已找到结果，但全部下载失败，请检查来源错误。',
    completedInfo: (downloaded, total) => `下载完成：${downloaded} / ${total}`,
    stoppedInfo: (downloaded, total) => `下载已停止：${downloaded} / ${total}`,
    stoppingInfo: '将在当前条目处理完成后停止...',
    taskFailed: '下载任务失败',
    addItemInfo: `已加入 ${localKbRef}`,
    addItemFailed: '加入条目失败',
    deleteItemConfirm: `确定删除这条结果吗？如果它已加入 ${localKbRef}，对应文档也会一并删除。`,
    deleteItemInfo: '结果已删除',
    deleteItemFailed: '删除结果失败',
    addAllInfo: (res) => `批量加入完成：成功 ${res?.success || 0}，失败 ${res?.failed || 0}`,
    addAllFailed: '批量加入结果失败',
    deleteSessionConfirm: `确定删除当前下载会话以及 ${localKbRef} 中已加入的文档吗？`,
    deleteSessionInfo: (res) => `已删除：结果 ${res?.deleted_items || 0}，文档 ${res?.deleted_docs || 0}`,
    deleteSessionFailed: '删除下载会话失败',
    deleteHistoryConfirm: (row) =>
      `确定删除历史关键词“${row?.keyword_display || ''}”以及相关本地文件吗？`,
    deleteHistoryInfo: (res) =>
      `历史记录已删除：会话 ${res?.deleted_sessions || 0}，条目 ${res?.deleted_items || 0}，文件 ${res?.deleted_files || 0}`,
    deleteHistoryFailed: '删除历史关键词失败',
    addHistoryInfo: (res) =>
      `历史批量加入完成：成功 ${res?.success || 0}，失败 ${res?.failed || 0}`,
    addHistoryFailed: '将历史关键词加入知识库失败',
    refreshHistoryInfo: '历史记录已刷新',
    refreshHistoryFailed: '刷新历史记录失败',
  };

  return { ...baseMessages, ...(messages || {}) };
}
