import { useCallback, useEffect, useMemo, useState } from 'react';

export default function useDocumentBrowserSelection({ documents, resetKey }) {
  const [selectedDocs, setSelectedDocs] = useState({});

  useEffect(() => {
    setSelectedDocs({});
  }, [resetKey]);

  const handleSelectDoc = useCallback((docId, datasetName) => {
    setSelectedDocs((previous) => {
      const list = previous[datasetName] || [];
      return {
        ...previous,
        [datasetName]: list.includes(docId)
          ? list.filter((id) => id !== docId)
          : [...list, docId],
      };
    });
  }, []);

  const handleSelectAllInDataset = useCallback(
    (datasetName) => {
      const datasetDocs = documents[datasetName] || [];
      setSelectedDocs((previous) => {
        const current = previous[datasetName] || [];
        return {
          ...previous,
          [datasetName]:
            current.length === datasetDocs.length ? [] : datasetDocs.map((doc) => doc.id),
        };
      });
    },
    [documents]
  );

  const isDocSelected = useCallback(
    (docId, datasetName) => (selectedDocs[datasetName] || []).includes(docId),
    [selectedDocs]
  );

  const isAllSelectedInDataset = useCallback(
    (datasetName) => {
      const datasetDocs = documents[datasetName] || [];
      const current = selectedDocs[datasetName] || [];
      return datasetDocs.length > 0 && current.length === datasetDocs.length;
    },
    [documents, selectedDocs]
  );

  const clearAllSelections = useCallback(() => setSelectedDocs({}), []);

  const clearTransferredMoveSelections = useCallback((results) => {
    const movedItems = Array.isArray(results) ? results : [];
    if (movedItems.length === 0) return;

    setSelectedDocs((previous) => {
      const next = { ...previous };
      let changed = false;

      movedItems.forEach((item) => {
        const sourceDatasetName = String(item?.sourceDatasetName || '').trim();
        const sourceDocId = String(item?.sourceDocId || '').trim();
        if (!sourceDatasetName || !sourceDocId) return;

        const current = Array.isArray(next[sourceDatasetName])
          ? next[sourceDatasetName]
          : [];
        if (!current.includes(sourceDocId)) return;

        next[sourceDatasetName] = current.filter((id) => id !== sourceDocId);
        changed = true;
      });

      return changed ? next : previous;
    });
  }, []);

  const selectedCount = useMemo(
    () => Object.values(selectedDocs).reduce((sum, list) => sum + list.length, 0),
    [selectedDocs]
  );

  return {
    selectedDocs,
    setSelectedDocs,
    selectedCount,
    handleSelectDoc,
    handleSelectAllInDataset,
    isDocSelected,
    isAllSelectedInDataset,
    clearAllSelections,
    clearTransferredMoveSelections,
  };
}
