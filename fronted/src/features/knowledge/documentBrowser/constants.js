export const ROOT = '';

const PREVIEW_SUPPORTED_EXTENSIONS = new Set([
  '.txt', '.md', '.csv', '.json', '.xml', '.log', '.svg', '.html', '.css', '.js',
  '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp',
  '.pdf', '.doc', '.docx', '.xlsx', '.xls', '.ppt', '.pptx',
]);

const getExtLower = (name = '') => {
  const s = String(name || '').trim().toLowerCase();
  const idx = s.lastIndexOf('.');
  if (idx < 0) return '';
  return s.slice(idx);
};

export const canPreviewFilename = (name = '') => PREVIEW_SUPPORTED_EXTENSIONS.has(getExtLower(name));

export const TEXT = {
  title: '\u6587\u6863\u6d4f\u89c8',
  desc: '\u6587\u6863\u6d4f\u89c8\u7684\u77e5\u8bc6\u5e93\u76ee\u5f55\u5c42\u7ea7\u4e0e\u77e5\u8bc6\u914d\u7f6e\u4fdd\u6301\u4e00\u81f4\u3002',
  root: '\u6839\u76ee\u5f55',
  folder: '\u6587\u4ef6\u5939',
  datasets: '\u77e5\u8bc6\u5e93\u6570\u91cf',
  docs: '\u6587\u6863\u603b\u6570',
  filter: '\u7b5b\u9009',
  filterPlaceholder: '\u8f93\u5165\u77e5\u8bc6\u5e93\u540d\u79f0\u3001ID \u6216\u76ee\u5f55\u5173\u952e\u8bcd',
  recent: '\u6700\u8fd1',
  clear: '\u6e05\u7a7a',
  noKb: '\u6682\u65e0\u77e5\u8bc6\u5e93',
  noMatch: '\u6ca1\u6709\u5339\u914d\u7684\u77e5\u8bc6\u5e93',
  noMatchDesc: '\u8bf7\u8c03\u6574\u5173\u952e\u8bcd\uff0c\u6216\u70b9\u51fb\u6e05\u7a7a\u663e\u793a\u5168\u90e8\u3002',
  expandAll: '\u5c55\u5f00\u5168\u90e8',
  collapseAll: '\u6298\u53e0\u5168\u90e8',
  refresh: '\u5237\u65b0',
  batch: '\u6279\u91cf\u4e0b\u8f7d',
  batchCopy: '\u6279\u91cf\u590d\u5236\u5230',
  batchMove: '\u6279\u91cf\u79fb\u52a8\u5230',
  confirm: '\u786e\u8ba4',
  cancel: '\u53d6\u6d88',
  targetKb: '\u76ee\u6807\u77e5\u8bc6\u5e93',
  transferTitleCopy: '\u590d\u5236\u6587\u6863',
  transferTitleMove: '\u79fb\u52a8\u6587\u6863',
  transferInProgress: '\u6279\u91cf\u5904\u7406\u8fdb\u5ea6',
  transferCurrent: '\u5f53\u524d',
  transferSuccess: '\u6210\u529f',
  transferFailed: '\u5931\u8d25',
  transferDone: '\u5df2\u5b8c\u6210',
  packing: '\u6253\u5305\u4e2d',
  clearSelection: '\u6e05\u9664\u9009\u62e9',
  loading: '\u52a0\u8f7d\u4e2d...',
  loadingDocs: '\u52a0\u8f7d\u6587\u6863\u4e2d...',
  noDocs: '\u5f53\u524d\u77e5\u8bc6\u5e93\u4e0b\u6682\u65e0\u6587\u6863',
  retry: 'Retry',
  docName: '\u6587\u6863\u540d\u79f0',
  view: '\u67e5\u770b',
  viewUnsupported: '\u5f53\u524d\u6587\u4ef6\u540e\u7f00\u4e0d\u652f\u6301\u5728\u7ebf\u9884\u89c8',
  viewing: '\u9884\u89c8\u4e2d',
  download: '\u4e0b\u8f7d',
  downloading: '\u4e0b\u8f7d\u4e2d',
  delete: '\u5220\u9664',
  copyTo: '\u590d\u5236\u5230',
  moveTo: '\u79fb\u52a8\u5230',
  deleteConfirm: '\u786e\u5b9a\u8981\u5220\u9664\u8be5\u6587\u6863\u5417\uff1f\u6b64\u64cd\u4f5c\u4e0d\u53ef\u6062\u590d\u3002',
  needOne: '\u8bf7\u81f3\u5c11\u9009\u62e9\u4e00\u4e2a\u6587\u6863',
  noPermission: '\u60a8\u6ca1\u6709\u88ab\u5206\u914d\u4efb\u4f55\u77e5\u8bc6\u5e93\u6743\u9650\uff0c\u8bf7\u8054\u7cfb\u7ba1\u7406\u5458',
  loadKbFail: '\u52a0\u8f7d\u77e5\u8bc6\u5e93\u5931\u8d25',
  loadDocFail: '\u52a0\u8f7d\u6587\u6863\u5931\u8d25',
  downloadFail: '\u4e0b\u8f7d\u5931\u8d25',
  deleteFail: '\u5220\u9664\u5931\u8d25',
  copyFail: '\u590d\u5236\u5931\u8d25',
  moveFail: '\u79fb\u52a8\u5931\u8d25',
  selectTargetKb: '\u8bf7\u8f93\u5165\u76ee\u6807\u77e5\u8bc6\u5e93\u540d\u79f0',
  noTargetKb: '\u6ca1\u6709\u53ef\u9009\u7684\u76ee\u6807\u77e5\u8bc6\u5e93',
  batchFail: '\u6279\u91cf\u4e0b\u8f7d\u5931\u8d25',
  cannotFindKb: '\u65e0\u6cd5\u627e\u5230\u77e5\u8bc6\u5e93',
  cannotFindDocPrefix: '\u65e0\u6cd5\u5728\u77e5\u8bc6\u5e93',
  currentFolder: '\u5f53\u524d\u76ee\u5f55',
  emptyFolder: '\u5f53\u524d\u76ee\u5f55\u4e0b\u6682\u65e0\u77e5\u8bc6\u5e93',
};
