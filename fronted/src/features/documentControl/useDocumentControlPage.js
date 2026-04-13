import { useCallback, useEffect, useMemo, useState } from 'react';
import documentControlApi from './api';

const DEFAULT_FILTERS = {
  query: '',
  docCode: '',
  title: '',
  documentType: '',
  productName: '',
  registrationRef: '',
  status: '',
};

const DEFAULT_DOCUMENT_FORM = {
  doc_code: '',
  title: '',
  document_type: '',
  target_kb_id: '',
  product_name: '',
  registration_ref: '',
  change_summary: '',
  file: null,
};

const DEFAULT_REVISION_FORM = {
  change_summary: '',
  file: null,
};

const DEFAULT_TEXT = {
  loadError: 'Failed to load controlled documents',
  createDocumentError: 'Failed to create controlled document',
  createDocumentSuccess: 'Controlled document created',
  createRevisionError: 'Failed to create revision',
  createRevisionSuccess: 'Revision created',
  transitionError: 'Failed to change revision status',
  transitionSuccess: 'Revision status updated',
};

const normalizeError = (message, fallback, mapErrorMessage) =>
  mapErrorMessage ? mapErrorMessage(message, fallback) : String(message || fallback || '');

export default function useDocumentControlPage({ text = DEFAULT_TEXT, mapErrorMessage } = {}) {
  const resolvedText = { ...DEFAULT_TEXT, ...(text || {}) };
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [savingDocument, setSavingDocument] = useState(false);
  const [savingRevision, setSavingRevision] = useState(false);
  const [transitioningRevisionId, setTransitioningRevisionId] = useState('');
  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState('');
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentForm, setDocumentForm] = useState(DEFAULT_DOCUMENT_FORM);
  const [revisionForm, setRevisionForm] = useState(DEFAULT_REVISION_FORM);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const resetMessages = useCallback(() => {
    setError('');
    setSuccess('');
  }, []);

  const fetchDocumentDetail = useCallback(
    async (controlledDocumentId) => {
      const cleanId = String(controlledDocumentId || '').trim();
      if (!cleanId) {
        setSelectedDocumentId('');
        setSelectedDocument(null);
        return null;
      }
      setDetailLoading(true);
      try {
        const document = await documentControlApi.getDocument(cleanId);
        setSelectedDocumentId(cleanId);
        setSelectedDocument(document);
        return document;
      } catch (requestError) {
        setError(normalizeError(requestError?.message, resolvedText.loadError, mapErrorMessage));
        setSelectedDocument(null);
        return null;
      } finally {
        setDetailLoading(false);
      }
    },
    [mapErrorMessage, resolvedText.loadError]
  );

  const loadDocuments = useCallback(
    async ({ nextFilters, preferredDocumentId, preferredDocument, clearMessages = true } = {}) => {
      const appliedFilters = nextFilters || filters;
      setLoading(true);
      if (clearMessages) {
        resetMessages();
      }
      try {
        const items = await documentControlApi.listDocuments({ ...appliedFilters, limit: 100 });
        setDocuments(items);
        const candidateId =
          preferredDocumentId ||
          selectedDocumentId ||
          String(items?.[0]?.controlled_document_id || '');
        const nextSelectedId =
          candidateId && items.some((item) => item.controlled_document_id === candidateId)
            ? candidateId
            : String(items?.[0]?.controlled_document_id || '');

        if (!nextSelectedId) {
          setSelectedDocumentId('');
          setSelectedDocument(null);
          return [];
        }

        if (
          preferredDocument &&
          String(preferredDocument.controlled_document_id || '') === nextSelectedId
        ) {
          setSelectedDocumentId(nextSelectedId);
          setSelectedDocument(preferredDocument);
          return items;
        }

        await fetchDocumentDetail(nextSelectedId);
        return items;
      } catch (requestError) {
        setDocuments([]);
        setSelectedDocumentId('');
        setSelectedDocument(null);
        setError(normalizeError(requestError?.message, resolvedText.loadError, mapErrorMessage));
        return [];
      } finally {
        setLoading(false);
      }
    },
    [
      fetchDocumentDetail,
      filters,
      mapErrorMessage,
      resetMessages,
      resolvedText.loadError,
      selectedDocumentId,
    ]
  );

  useEffect(() => {
    loadDocuments({ nextFilters: DEFAULT_FILTERS });
    // Initial load only; later refreshes are explicit via search or mutations.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const currentRevision = selectedDocument?.current_revision || null;
  const effectiveRevision = selectedDocument?.effective_revision || null;
  const revisions = useMemo(
    () => (Array.isArray(selectedDocument?.revisions) ? selectedDocument.revisions : []),
    [selectedDocument]
  );

  const handleFilterChange = useCallback((field, value) => {
    setFilters((previous) => ({ ...previous, [field]: value }));
  }, []);

  const handleSearch = useCallback(async () => {
    await loadDocuments({ nextFilters: filters });
  }, [filters, loadDocuments]);

  const handleSelectDocument = useCallback(
    async (controlledDocumentId) => {
      resetMessages();
      await fetchDocumentDetail(controlledDocumentId);
    },
    [fetchDocumentDetail, resetMessages]
  );

  const handleCreateDocument = useCallback(async () => {
    resetMessages();
    if (!documentForm.file) {
      setError(normalizeError('file_required', resolvedText.createDocumentError, mapErrorMessage));
      return null;
    }
    setSavingDocument(true);
    try {
      const document = await documentControlApi.createDocument(documentForm);
      setDocumentForm(DEFAULT_DOCUMENT_FORM);
      setSelectedDocumentId(String(document.controlled_document_id || ''));
      setSelectedDocument(document);
      setSuccess(resolvedText.createDocumentSuccess);
      await loadDocuments({
        nextFilters: filters,
        preferredDocumentId: String(document.controlled_document_id || ''),
        preferredDocument: document,
        clearMessages: false,
      });
      return document;
    } catch (requestError) {
      setError(
        normalizeError(requestError?.message, resolvedText.createDocumentError, mapErrorMessage)
      );
      return null;
    } finally {
      setSavingDocument(false);
    }
  }, [
    documentForm,
    filters,
    loadDocuments,
    mapErrorMessage,
    resetMessages,
    resolvedText.createDocumentError,
    resolvedText.createDocumentSuccess,
  ]);

  const handleCreateRevision = useCallback(async () => {
    resetMessages();
    if (!selectedDocumentId) {
      setError(
        normalizeError('document_required', resolvedText.createRevisionError, mapErrorMessage)
      );
      return null;
    }
    if (!revisionForm.file) {
      setError(normalizeError('file_required', resolvedText.createRevisionError, mapErrorMessage));
      return null;
    }
    setSavingRevision(true);
    try {
      const document = await documentControlApi.createRevision(selectedDocumentId, revisionForm);
      setRevisionForm(DEFAULT_REVISION_FORM);
      setSelectedDocument(document);
      setSuccess(resolvedText.createRevisionSuccess);
      await loadDocuments({
        nextFilters: filters,
        preferredDocumentId: selectedDocumentId,
        preferredDocument: document,
        clearMessages: false,
      });
      return document;
    } catch (requestError) {
      setError(
        normalizeError(requestError?.message, resolvedText.createRevisionError, mapErrorMessage)
      );
      return null;
    } finally {
      setSavingRevision(false);
    }
  }, [
    filters,
    loadDocuments,
    mapErrorMessage,
    resetMessages,
    resolvedText.createRevisionError,
    resolvedText.createRevisionSuccess,
    revisionForm,
    selectedDocumentId,
  ]);

  const handleTransitionRevision = useCallback(
    async (controlledRevisionId, targetStatus) => {
      resetMessages();
      setTransitioningRevisionId(String(controlledRevisionId || ''));
      try {
        const document = await documentControlApi.transitionRevision(controlledRevisionId, {
          target_status: targetStatus,
        });
        setSelectedDocument(document);
        setSuccess(resolvedText.transitionSuccess);
        await loadDocuments({
          nextFilters: filters,
          preferredDocumentId: String(document.controlled_document_id || ''),
          preferredDocument: document,
          clearMessages: false,
        });
        return document;
      } catch (requestError) {
        setError(normalizeError(requestError?.message, resolvedText.transitionError, mapErrorMessage));
        return null;
      } finally {
        setTransitioningRevisionId('');
      }
    },
    [
      filters,
      loadDocuments,
      mapErrorMessage,
      resetMessages,
      resolvedText.transitionError,
      resolvedText.transitionSuccess,
    ]
  );

  return {
    loading,
    detailLoading,
    savingDocument,
    savingRevision,
    transitioningRevisionId,
    filters,
    documents,
    selectedDocumentId,
    selectedDocument,
    currentRevision,
    effectiveRevision,
    revisions,
    documentForm,
    revisionForm,
    error,
    success,
    setDocumentForm,
    setRevisionForm,
    handleFilterChange,
    handleSearch,
    handleSelectDocument,
    handleCreateDocument,
    handleCreateRevision,
    handleTransitionRevision,
  };
}
