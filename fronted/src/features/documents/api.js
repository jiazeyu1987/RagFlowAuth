import documentClient, { DOCUMENT_SOURCE } from '../../shared/documents/documentClient';

export { DOCUMENT_SOURCE };

export const documentsApi = {
  preview(ref) {
    return documentClient.preview(ref);
  },

  downloadBlob(ref) {
    return documentClient.downloadBlob(ref);
  },

  downloadToBrowser(ref) {
    return documentClient.downloadToBrowser(ref);
  },

  batchDownloadKnowledgeToBrowser(docIds) {
    return documentClient.batchDownloadKnowledgeToBrowser(docIds);
  },

  batchDownloadRagflowToBrowser(documents) {
    return documentClient.batchDownloadRagflowToBrowser(documents);
  },

  deleteDocument(ref) {
    return documentClient.delete(ref);
  },

  uploadKnowledge(file, kbId) {
    return documentClient.uploadKnowledge(file, kbId);
  },

  onlyofficeEditorConfig(ref) {
    return documentClient.onlyofficeEditorConfig(ref);
  },
};

export default documentsApi;
