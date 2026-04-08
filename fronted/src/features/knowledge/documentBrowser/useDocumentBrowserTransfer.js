import { useCallback, useEffect, useState } from 'react';
import { documentBrowserApi } from './api';
import { TEXT } from './constants';

export default function useDocumentBrowserTransfer({
  resetKey,
  selectedDocs,
  setSelectedDocs,
  transferTargetOptions,
  fetchDocumentsForDataset,
  recordDatasetUsage,
  clearTransferredMoveSelections,
  setActionLoading,
  setError,
}) {
  const [transferDialog, setTransferDialog] = useState(null);
  const [batchTransferProgress, setBatchTransferProgress] = useState(null);

  useEffect(() => {
    setTransferDialog(null);
    setBatchTransferProgress(null);
  }, [resetKey]);

  const openSingleTransferDialog = useCallback(
    (docId, sourceDatasetName, operation) => {
      recordDatasetUsage(sourceDatasetName);
      const candidates = transferTargetOptions.filter(
        (name) => name !== sourceDatasetName
      );
      if (!candidates.length) {
        setError(TEXT.noTargetKb);
        return;
      }

      setTransferDialog({
        scope: 'single',
        operation,
        docId,
        sourceDatasetName,
        targetDatasetName: candidates[0],
      });
    },
    [recordDatasetUsage, setError, transferTargetOptions]
  );

  const openBatchTransferDialog = useCallback(
    (operation) => {
      if (!transferTargetOptions.length) {
        setError(TEXT.noTargetKb);
        return;
      }

      setTransferDialog({
        scope: 'batch',
        operation,
        docId: '',
        sourceDatasetName: '',
        targetDatasetName: transferTargetOptions[0],
      });
    },
    [setError, transferTargetOptions]
  );

  const collectSelectedTransferItems = useCallback(
    (targetDatasetName) => {
      const items = [];
      Object.entries(selectedDocs).forEach(([sourceDatasetName, docIds]) => {
        docIds.forEach((docId) => {
          if (!docId || !sourceDatasetName || sourceDatasetName === targetDatasetName) {
            return;
          }
          items.push({
            docId,
            sourceDatasetName,
            targetDatasetName,
          });
        });
      });
      return items;
    },
    [selectedDocs]
  );

  const executeSingleTransfer = useCallback(
    async ({ docId, sourceDatasetName, targetDatasetName, operation }) => {
      try {
        setActionLoading((previous) => ({ ...previous, [`${docId}-${operation}`]: true }));
        await documentBrowserApi.transferDocument(
          docId,
          sourceDatasetName,
          targetDatasetName,
          operation
        );
        await Promise.all([
          fetchDocumentsForDataset(sourceDatasetName),
          fetchDocumentsForDataset(targetDatasetName),
        ]);

        if (operation === 'move') {
          setSelectedDocs((previous) => {
            const list = previous[sourceDatasetName] || [];
            if (!list.includes(docId)) return previous;
            return {
              ...previous,
              [sourceDatasetName]: list.filter((id) => id !== docId),
            };
          });
        }
      } catch (requestError) {
        setError(
          requestError?.message || (operation === 'move' ? TEXT.moveFail : TEXT.copyFail)
        );
      } finally {
        setActionLoading((previous) => ({ ...previous, [`${docId}-${operation}`]: false }));
      }
    },
    [fetchDocumentsForDataset, setActionLoading, setError, setSelectedDocs]
  );

  const executeBatchTransfer = useCallback(
    async ({ targetDatasetName, operation }) => {
      const items = collectSelectedTransferItems(targetDatasetName);
      if (!items.length) {
        setError(TEXT.needOne);
        return;
      }

      const progress = {
        operation,
        total: items.length,
        processed: 0,
        success: 0,
        failed: 0,
        current: targetDatasetName,
        done: false,
      };

      setBatchTransferProgress(progress);
      const loadingKey = operation === 'move' ? 'batch-move' : 'batch-copy';
      setActionLoading((previous) => ({ ...previous, [loadingKey]: true }));

      try {
        const result = await documentBrowserApi.transferDocumentsBatch(items, operation);
        const affected = new Set([targetDatasetName]);
        items.forEach((item) => affected.add(item.sourceDatasetName));

        await Promise.all(
          Array.from(affected).map((datasetName) => fetchDocumentsForDataset(datasetName))
        );

        if (operation === 'move') {
          clearTransferredMoveSelections(result.results);
        }

        setBatchTransferProgress({
          ...progress,
          processed: result.total,
          success: result.successCount,
          failed: result.failedCount,
          current: '',
          done: true,
        });

        if (result.failedCount > 0) {
          const firstFailed = result.failed[0];
          window.alert(
            `Done ${result.successCount}/${result.total}, failed ${result.failedCount}\nSample: ${firstFailed.sourceDatasetName}/${firstFailed.docId}: ${firstFailed.detail}`
          );
        }
      } catch (requestError) {
        setError(
          requestError?.message || (operation === 'move' ? TEXT.moveFail : TEXT.copyFail)
        );
        setBatchTransferProgress({
          ...progress,
          current: '',
          done: true,
        });
      } finally {
        setActionLoading((previous) => ({ ...previous, [loadingKey]: false }));
      }
    },
    [
      clearTransferredMoveSelections,
      collectSelectedTransferItems,
      fetchDocumentsForDataset,
      setActionLoading,
      setError,
    ]
  );

  const handleTransferConfirm = useCallback(async () => {
    if (!transferDialog?.targetDatasetName) {
      setError(TEXT.selectTargetKb);
      return;
    }

    const payload = { ...transferDialog };
    setTransferDialog(null);
    if (payload.scope === 'single') {
      await executeSingleTransfer(payload);
      return;
    }
    await executeBatchTransfer(payload);
  }, [executeBatchTransfer, executeSingleTransfer, setError, transferDialog]);

  return {
    transferDialog,
    setTransferDialog,
    batchTransferProgress,
    setBatchTransferProgress,
    openSingleTransferDialog,
    openBatchTransferDialog,
    handleTransferConfirm,
  };
}
