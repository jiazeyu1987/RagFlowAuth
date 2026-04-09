import { useCallback, useState } from 'react';
import { auditApi } from './api';
import { createVersionsDialogState } from './documentAuditHelpers';
import { mapUserFacingErrorMessage } from '../../shared/errors/userFacingErrorMessages';

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
        error: mapUserFacingErrorMessage(requestError?.message, '加载版本历史失败'),
      }));
    }
  }, []);

  return {
    versionsDialog,
    closeVersionsDialog,
    openVersionsDialog,
  };
}
