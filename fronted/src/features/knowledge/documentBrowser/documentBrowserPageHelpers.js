import { DOCUMENT_SOURCE } from '../../../shared/documents/constants';
import { ROOT, TEXT } from './constants';
import { pathNodes } from './treeUtils';

export function filterVisibleDatasets(datasetsWithFolders, datasetFilterKeyword) {
  const normalizedKeyword = String(datasetFilterKeyword || '').trim().toLowerCase();
  if (!normalizedKeyword) return datasetsWithFolders;

  return datasetsWithFolders.filter((dataset) => {
    const folderText =
      dataset.node_path && dataset.node_path !== '/' ? `${TEXT.root} ${dataset.node_path}` : TEXT.root;

    return (
      String(dataset.name || '').toLowerCase().includes(normalizedKeyword) ||
      String(dataset.id || '').toLowerCase().includes(normalizedKeyword) ||
      folderText.toLowerCase().includes(normalizedKeyword)
    );
  });
}

export function buildVisibleNodeIds(visibleDatasets, indexesById) {
  const ids = new Set();

  visibleDatasets.forEach((dataset) => {
    pathNodes(dataset.node_id, indexesById).forEach((node) => ids.add(node.id));
  });

  return ids;
}

export function buildFolderBreadcrumb(currentFolderId, indexesById) {
  return [
    { id: ROOT, name: TEXT.root },
    ...pathNodes(currentFolderId, indexesById).map((node) => ({
      id: node.id,
      name: node.name || TEXT.folder,
    })),
  ];
}

export function buildDatasetsInCurrentFolder(visibleDatasets, currentFolderId) {
  const list = visibleDatasets.filter((dataset) => (dataset.node_id || ROOT) === currentFolderId);

  return list.sort((left, right) =>
    String(left.name || '').localeCompare(String(right.name || ''), 'zh-Hans-CN')
  );
}

export function buildTransferTargetOptions(datasetsWithFolders) {
  const names = datasetsWithFolders
    .map((item) => String(item?.name || '').trim())
    .filter(Boolean);

  return Array.from(new Set(names)).sort((left, right) => left.localeCompare(right, 'zh-Hans-CN'));
}

export function buildExpandedNodeIds(nodeId, indexesById) {
  return pathNodes(nodeId, indexesById).map((node) => node.id);
}

export function resolveDatasetReference(datasetRef, datasetsWithFolders) {
  if (!datasetRef) return null;
  if (typeof datasetRef !== 'string') return datasetRef;

  return (
    datasetsWithFolders.find((item) => item.name === datasetRef || item.id === datasetRef) || null
  );
}

export function buildPreviewTarget(docId, datasetName, documentsByDataset) {
  const doc = documentsByDataset[datasetName]?.find((item) => item.id === docId);

  return {
    source: DOCUMENT_SOURCE.RAGFLOW,
    docId,
    datasetName,
    filename: doc?.name || `document_${docId}`,
  };
}

export function buildBatchDownloadItems(selectedDocs, documentsByDataset) {
  const items = [];

  Object.entries(selectedDocs).forEach(([datasetName, docIds]) => {
    docIds.forEach((docId) => {
      const doc = (documentsByDataset[datasetName] || []).find((item) => item.id === docId);
      if (!doc) return;

      items.push({
        doc_id: docId,
        dataset: datasetName,
        name: doc.name,
      });
    });
  });

  return items;
}
