export const LIST_LIMIT = 2000;

export const createVersionsDialogState = () => ({
  open: false,
  loading: false,
  error: '',
  doc: null,
  items: [],
  currentDocId: '',
  logicalDocId: '',
});

export const sortDocuments = (items) =>
  [...items].sort(
    (left, right) =>
      Number(right?.reviewed_at_ms || right?.uploaded_at_ms || 0) -
      Number(left?.reviewed_at_ms || left?.uploaded_at_ms || 0)
  );

export const collectKnowledgeBases = ({ documents, deletions, downloads }) => {
  const values = new Set();
  documents.forEach((item) => {
    if (item?.kb_id) values.add(item.kb_id);
  });
  deletions.forEach((item) => {
    if (item?.kb_id) values.add(item.kb_id);
  });
  downloads.forEach((item) => {
    if (item?.kb_id) values.add(item.kb_id);
  });
  return Array.from(values);
};

export const filterDocuments = ({ documents, filterKb, filterStatus }) =>
  documents.filter((document) => {
    if (filterKb && document.kb_id !== filterKb) return false;
    if (filterStatus && document.status !== filterStatus) return false;
    return true;
  });

export const filterByKnowledgeBase = ({ items, filterKb }) =>
  items.filter((item) => {
    if (filterKb && item.kb_id !== filterKb) return false;
    return true;
  });

export const formatTime = (timestampMs) => {
  if (!timestampMs) return '-';
  return new Date(Number(timestampMs)).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};
