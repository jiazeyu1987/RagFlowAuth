import React from 'react';

import { documentsApi } from '../../../documents/api';
import TransferDialog from './TransferDialog';
import { DocumentPreviewModal } from '../../../../shared/documents/preview/DocumentPreviewModal';

export default function DocumentBrowserDialogs({
  canDownload,
  handleTransferConfirm,
  previewOpen,
  previewTarget,
  selectedCount,
  setPreviewOpen,
  setPreviewTarget,
  setTransferDialog,
  transferDialog,
  transferTargetOptions,
}) {
  return (
    <>
      <DocumentPreviewModal
        open={previewOpen}
        target={previewTarget}
        onClose={() => {
          setPreviewOpen(false);
          setPreviewTarget(null);
        }}
        canDownloadFiles={typeof canDownload === 'function' ? !!canDownload() : false}
        documentApi={documentsApi}
      />
      <TransferDialog
        transferDialog={transferDialog}
        selectedCount={selectedCount}
        transferTargetOptions={transferTargetOptions}
        onClose={() => setTransferDialog(null)}
        onConfirm={handleTransferConfirm}
        onChangeTarget={(targetDatasetName) =>
          setTransferDialog((previous) => ({ ...previous, targetDatasetName }))
        }
      />
    </>
  );
}
