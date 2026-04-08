import { useMemo } from 'react';

import {
  buildDatasetsInCurrentFolder,
  buildFolderBreadcrumb,
  buildTransferTargetOptions,
  buildVisibleNodeIds,
  filterVisibleDatasets,
} from './documentBrowserPageHelpers';

export default function useDocumentBrowserDerivedState({
  currentFolderId,
  datasetFilterKeyword,
  datasetsWithFolders,
  documents,
  indexes,
}) {
  const visibleDatasets = useMemo(
    () => filterVisibleDatasets(datasetsWithFolders, datasetFilterKeyword),
    [datasetFilterKeyword, datasetsWithFolders]
  );

  const visibleNodeIds = useMemo(
    () => buildVisibleNodeIds(visibleDatasets, indexes.byId),
    [indexes.byId, visibleDatasets]
  );

  const folderBreadcrumb = useMemo(
    () => buildFolderBreadcrumb(currentFolderId, indexes.byId),
    [currentFolderId, indexes.byId]
  );

  const datasetsInCurrentFolder = useMemo(
    () => buildDatasetsInCurrentFolder(visibleDatasets, currentFolderId),
    [currentFolderId, visibleDatasets]
  );

  const transferTargetOptions = useMemo(
    () => buildTransferTargetOptions(datasetsWithFolders),
    [datasetsWithFolders]
  );

  const totalDocs = useMemo(
    () =>
      visibleDatasets.reduce(
        (sum, dataset) => sum + (documents[dataset.name] || []).length,
        0
      ),
    [documents, visibleDatasets]
  );

  return {
    indexes,
    datasetsWithFolders,
    visibleDatasets,
    visibleNodeIds,
    folderBreadcrumb,
    datasetsInCurrentFolder,
    transferTargetOptions,
    totalDocs,
  };
}
