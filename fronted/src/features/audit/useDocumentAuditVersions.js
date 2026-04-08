import { useCallback, useState } from 'react';
import { auditApi } from './api';
import { createVersionsDialogState } from './documentAuditHelpers';

export default function useDocumentAuditVersions() {
  const [versionsDialog, setVersionsDialog] = useState(createVersionsDialogState);

  const closeVersionsDialog = useCallback(() => {
    setVersionsDialog(createVersionsDialogState());
  }, []);

  const openVersionsDialog = useCallback(async (doc) => {
    setVersionsDialog({
      ...createVersionsDialogState(),
      open: true,
      loading: true,
      doc,
    });

    try {
      const payload = await auditApi.listDocumentVersions(doc.doc_id);
      setVersionsDialog({
        open: true,
        loading: false,
        error: '',
        doc,
        items: payload.versions,
        currentDocId: payload.currentDocId,
        logicalDocId: payload.logicalDocId,
      });
    } catch (requestError) {
      setVersionsDialog((previous) => ({
        ...previous,
        loading: false,
        error: requestError?.message || '\u52a0\u8f7d\u7248\u672c\u5386\u53f2\u5931\u8d25',
      }));
    }
  }, []);

  return {
    versionsDialog,
    closeVersionsDialog,
    openVersionsDialog,
  };
}
