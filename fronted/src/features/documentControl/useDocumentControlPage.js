import { useCallback, useEffect, useMemo, useState } from 'react';
import documentControlApi from './api';
import operationApprovalApi from '../operationApproval/api';
import trainingComplianceApi from '../trainingCompliance/api';
import qualitySystemConfigApi from '../qualitySystemConfig/api';

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
  file_subtype: '',
  usage_scope: '',
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
  approvalDetailError: 'Failed to load approval request detail',
  trainingLoadError: 'Failed to load training assignments',
  trainingGateLoadError: 'Failed to load training gate',
  trainingGateSaveError: 'Failed to save training gate',
  trainingGateSaveSuccess: 'Training gate saved',
  trainingGenerateError: 'Failed to generate training assignments',
  trainingGenerateSuccess: 'Training assignments generated',
  distributionLoadError: 'Failed to load distribution departments',
  distributionSaveError: 'Failed to save distribution departments',
  distributionSaveSuccess: 'Distribution departments saved',
  publishError: 'Failed to publish revision',
  publishSuccess: 'Revision published',
  manualReleaseCompleteError: 'Failed to complete manual archive release',
  manualReleaseCompleteSuccess: 'Manual archive release completed',
  departmentAcksLoadError: 'Failed to load department acknowledgments',
  departmentAckConfirmError: 'Failed to confirm department acknowledgment',
  departmentAckConfirmSuccess: 'Department acknowledgment recorded',
  departmentAckRemindError: 'Failed to send overdue reminders',
  departmentAckRemindSuccess: 'Overdue reminders sent',
  obsoleteInitiateError: 'Failed to initiate obsolete flow',
  obsoleteInitiateSuccess: 'Obsolete request initiated',
  obsoleteApproveError: 'Failed to approve obsolete flow',
  obsoleteApproveSuccess: 'Obsolete request approved',
  destructionConfirmError: 'Failed to confirm destruction',
  destructionConfirmSuccess: 'Destruction confirmation recorded',
  retentionLoadError: 'Failed to load retention information',
  fileSubtypeLoadError: 'Failed to load file subtypes',
  matrixPreviewLoadError: 'Failed to load matrix preview',
  createDocumentError: 'Failed to create controlled document',
  createDocumentSuccess: 'Controlled document created',
  createRevisionError: 'Failed to create revision',
  createRevisionSuccess: 'Revision created',
  submitApprovalError: 'Failed to submit revision for approval',
  submitApprovalSuccess: 'Revision submitted for approval',
  approveStepError: 'Failed to approve revision step',
  approveStepSuccess: 'Approval recorded',
  rejectStepError: 'Failed to reject revision step',
  rejectStepSuccess: 'Rejection recorded',
  remindApprovalError: 'Failed to send approval overdue reminder',
  remindApprovalSuccess: 'Approval overdue reminder sent',
  addSignError: 'Failed to add an additional approver',
  addSignSuccess: 'Additional approver added',
};

const normalizeError = (message, fallback, mapErrorMessage) =>
  mapErrorMessage ? mapErrorMessage(message, fallback) : String(message || fallback || '');

export default function useDocumentControlPage({ text = DEFAULT_TEXT, mapErrorMessage, features } = {}) {
  const resolvedText = { ...DEFAULT_TEXT, ...(text || {}) };
  const resolvedFeatures = features && typeof features === 'object' ? features : {};
  const enableTraining = resolvedFeatures.enableTraining !== false;
  const enableDepartmentAcks = resolvedFeatures.enableDepartmentAcks !== false;
  const enableRetention = resolvedFeatures.enableRetention !== false;

  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [savingDocument, setSavingDocument] = useState(false);
  const [savingRevision, setSavingRevision] = useState(false);
  const [workflowAction, setWorkflowAction] = useState('');
  const [workflowActionRevisionId, setWorkflowActionRevisionId] = useState('');

  const [filters, setFilters] = useState(DEFAULT_FILTERS);
  const [documents, setDocuments] = useState([]);
  const [selectedDocumentId, setSelectedDocumentId] = useState('');
  const [selectedDocument, setSelectedDocument] = useState(null);
  const [documentForm, setDocumentForm] = useState(DEFAULT_DOCUMENT_FORM);
  const [revisionForm, setRevisionForm] = useState(DEFAULT_REVISION_FORM);

  const [approvalDetailLoading, setApprovalDetailLoading] = useState(false);
  const [approvalDetail, setApprovalDetail] = useState(null);
  const [approvalDetailError, setApprovalDetailError] = useState('');
  const [fileSubtypeOptions, setFileSubtypeOptions] = useState([]);
  const [fileSubtypeOptionsError, setFileSubtypeOptionsError] = useState('');
  const [matrixPreviewLoading, setMatrixPreviewLoading] = useState(false);
  const [matrixPreview, setMatrixPreview] = useState(null);
  const [matrixPreviewError, setMatrixPreviewError] = useState('');

  const [trainingLoading, setTrainingLoading] = useState(false);
  const [trainingGateLoading, setTrainingGateLoading] = useState(false);
  const [trainingGate, setTrainingGate] = useState(null);
  const [trainingGateError, setTrainingGateError] = useState('');
  const [trainingAssignments, setTrainingAssignments] = useState([]);
  const [trainingError, setTrainingError] = useState('');
  const [trainingGenerateLoading, setTrainingGenerateLoading] = useState(false);
  const [generatedTrainingAssignments, setGeneratedTrainingAssignments] = useState([]);

  const [distributionDepartmentsLoading, setDistributionDepartmentsLoading] = useState(false);
  const [distributionDepartmentIds, setDistributionDepartmentIds] = useState([]);
  const [distributionDepartmentsError, setDistributionDepartmentsError] = useState('');

  const [departmentAcksLoading, setDepartmentAcksLoading] = useState(false);
  const [departmentAcks, setDepartmentAcks] = useState([]);
  const [departmentAcksError, setDepartmentAcksError] = useState('');

  const [retentionLoading, setRetentionLoading] = useState(false);
  const [retentionRecord, setRetentionRecord] = useState(null);
  const [retentionError, setRetentionError] = useState('');

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
    // 仅在初始化时自动加载，后续刷新通过搜索或操作显式触发。
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    let cancelled = false;
    setFileSubtypeOptionsError('');
    qualitySystemConfigApi
      .getConfig()
      .then((payload) => {
        if (cancelled) return;
        const items = Array.isArray(payload?.file_categories) ? payload.file_categories : [];
        setFileSubtypeOptions(items);
      })
      .catch((requestError) => {
        if (cancelled) return;
        setFileSubtypeOptions([]);
        setFileSubtypeOptionsError(
          normalizeError(requestError?.message, resolvedText.fileSubtypeLoadError, mapErrorMessage)
        );
      });
    return () => {
      cancelled = true;
    };
  }, [mapErrorMessage, resolvedText.fileSubtypeLoadError]);

  const currentRevision = selectedDocument?.current_revision || null;
  const effectiveRevision = selectedDocument?.effective_revision || null;
  const revisions = useMemo(
    () => (Array.isArray(selectedDocument?.revisions) ? selectedDocument.revisions : []),
    [selectedDocument]
  );

  const currentRevisionId = useMemo(() => {
    const raw = currentRevision?.controlled_revision_id;
    return raw ? String(raw).trim() : '';
  }, [currentRevision?.controlled_revision_id]);

  const currentKbDocId = useMemo(() => {
    const raw = currentRevision?.kb_doc_id;
    return raw ? String(raw).trim() : '';
  }, [currentRevision?.kb_doc_id]);

  const approvalRequestId = useMemo(() => {
    const raw = currentRevision?.approval_request_id;
    return raw ? String(raw).trim() : '';
  }, [currentRevision?.approval_request_id]);

  useEffect(() => {
    let cancelled = false;
    setMatrixPreview(null);
    setMatrixPreviewError('');

    if (!currentRevisionId || approvalRequestId || !['draft', 'approval_rejected'].includes(String(currentRevision?.status || ''))) {
      setMatrixPreviewLoading(false);
      return () => {};
    }

    setMatrixPreviewLoading(true);
    documentControlApi
      .previewRevisionApprovalMatrix(currentRevisionId)
      .then((result) => {
        if (cancelled) return;
        setMatrixPreview(result);
      })
      .catch((requestError) => {
        if (cancelled) return;
        setMatrixPreviewError(
          normalizeError(requestError?.message, resolvedText.matrixPreviewLoadError, mapErrorMessage)
        );
      })
      .finally(() => {
        if (cancelled) return;
        setMatrixPreviewLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [
    approvalRequestId,
    currentRevision?.status,
    currentRevisionId,
    mapErrorMessage,
    resolvedText.matrixPreviewLoadError,
  ]);

  useEffect(() => {
    let cancelled = false;
    setApprovalDetail(null);
    setApprovalDetailError('');

    if (!approvalRequestId) {
      setApprovalDetailLoading(false);
      return () => {};
    }

    setApprovalDetailLoading(true);
    operationApprovalApi
      .getRequest(approvalRequestId)
      .then((detail) => {
        if (cancelled) return;
        setApprovalDetail(detail);
      })
      .catch((requestError) => {
        if (cancelled) return;
        setApprovalDetailError(
          normalizeError(requestError?.message, resolvedText.approvalDetailError, mapErrorMessage)
        );
      })
      .finally(() => {
        if (cancelled) return;
        setApprovalDetailLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [approvalRequestId, mapErrorMessage, resolvedText.approvalDetailError]);

  useEffect(() => {
    let cancelled = false;
    setTrainingGate(null);
    setTrainingGateError('');

    if (!enableTraining || !currentRevisionId) {
      setTrainingGateLoading(false);
      return () => {};
    }

    setTrainingGateLoading(true);
    trainingComplianceApi
      .getRevisionGate(currentRevisionId)
      .then((item) => {
        if (cancelled) return;
        setTrainingGate(item);
      })
      .catch((requestError) => {
        if (cancelled) return;
        setTrainingGateError(
          normalizeError(requestError?.message, resolvedText.trainingGateLoadError, mapErrorMessage)
        );
      })
      .finally(() => {
        if (cancelled) return;
        setTrainingGateLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [currentRevisionId, enableTraining, mapErrorMessage, resolvedText.trainingGateLoadError]);

  useEffect(() => {
    let cancelled = false;
    setTrainingAssignments([]);
    setGeneratedTrainingAssignments([]);
    setTrainingError('');

    if (!enableTraining || !currentRevisionId) {
      setTrainingLoading(false);
      return () => {};
    }

    setTrainingLoading(true);
    trainingComplianceApi
      .listAssignments({ limit: 200 })
      .then((items) => {
        if (cancelled) return;
        const filtered = (Array.isArray(items) ? items : []).filter(
          (item) => String(item?.controlled_revision_id || '') === currentRevisionId
        );
        setTrainingAssignments(filtered);
      })
      .catch((requestError) => {
        if (cancelled) return;
        setTrainingError(
          normalizeError(requestError?.message, resolvedText.trainingLoadError, mapErrorMessage)
        );
      })
      .finally(() => {
        if (cancelled) return;
        setTrainingLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [currentRevisionId, enableTraining, mapErrorMessage, resolvedText.trainingLoadError]);

  const loadDistributionDepartments = useCallback(async (controlledDocumentId) => {
    const cleanId = String(controlledDocumentId || '').trim();
    setDistributionDepartmentIds([]);
    setDistributionDepartmentsError('');
    if (!cleanId) {
      setDistributionDepartmentsLoading(false);
      return [];
    }
    setDistributionDepartmentsLoading(true);
    try {
      const items = await documentControlApi.getDistributionDepartments(cleanId);
      setDistributionDepartmentIds(Array.isArray(items) ? items : []);
      return Array.isArray(items) ? items : [];
    } catch (requestError) {
      setDistributionDepartmentsError(
        normalizeError(requestError?.message, resolvedText.distributionLoadError, mapErrorMessage)
      );
      return [];
    } finally {
      setDistributionDepartmentsLoading(false);
    }
  }, [mapErrorMessage, resolvedText.distributionLoadError]);

  useEffect(() => {
    let cancelled = false;
    setDistributionDepartmentIds([]);
    setDistributionDepartmentsError('');

    if (!enableDepartmentAcks || !selectedDocumentId) {
      setDistributionDepartmentsLoading(false);
      return () => {};
    }

    setDistributionDepartmentsLoading(true);
    documentControlApi
      .getDistributionDepartments(selectedDocumentId)
      .then((items) => {
        if (cancelled) return;
        setDistributionDepartmentIds(Array.isArray(items) ? items : []);
      })
      .catch((requestError) => {
        if (cancelled) return;
        setDistributionDepartmentsError(
          normalizeError(requestError?.message, resolvedText.distributionLoadError, mapErrorMessage)
        );
      })
      .finally(() => {
        if (cancelled) return;
        setDistributionDepartmentsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [selectedDocumentId, enableDepartmentAcks, mapErrorMessage, resolvedText.distributionLoadError]);

  const loadDepartmentAcks = useCallback(async (controlledRevisionId) => {
    const cleanId = String(controlledRevisionId || '').trim();
    setDepartmentAcks([]);
    setDepartmentAcksError('');
    if (!cleanId) {
      setDepartmentAcksLoading(false);
      return [];
    }
    setDepartmentAcksLoading(true);
    try {
      const items = await documentControlApi.listRevisionDepartmentAcks(cleanId);
      setDepartmentAcks(Array.isArray(items) ? items : []);
      return Array.isArray(items) ? items : [];
    } catch (requestError) {
      setDepartmentAcksError(
        normalizeError(requestError?.message, resolvedText.departmentAcksLoadError, mapErrorMessage)
      );
      return [];
    } finally {
      setDepartmentAcksLoading(false);
    }
  }, [mapErrorMessage, resolvedText.departmentAcksLoadError]);

  useEffect(() => {
    let cancelled = false;
    setDepartmentAcks([]);
    setDepartmentAcksError('');

    if (!enableDepartmentAcks || !currentRevisionId) {
      setDepartmentAcksLoading(false);
      return () => {};
    }

    setDepartmentAcksLoading(true);
    documentControlApi
      .listRevisionDepartmentAcks(currentRevisionId)
      .then((items) => {
        if (cancelled) return;
        setDepartmentAcks(Array.isArray(items) ? items : []);
      })
      .catch((requestError) => {
        if (cancelled) return;
        setDepartmentAcksError(
          normalizeError(requestError?.message, resolvedText.departmentAcksLoadError, mapErrorMessage)
        );
      })
      .finally(() => {
        if (cancelled) return;
        setDepartmentAcksLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [currentRevisionId, enableDepartmentAcks, mapErrorMessage, resolvedText.departmentAcksLoadError]);

  useEffect(() => {
    let cancelled = false;
    setRetentionRecord(null);
    setRetentionError('');

    const shouldLoad = enableRetention && String(currentRevision?.status || '') === 'obsolete';
    if (!shouldLoad || !currentKbDocId) {
      setRetentionLoading(false);
      return () => {};
    }

    setRetentionLoading(true);
    documentControlApi
      .listRetiredDocuments({ limit: 200 })
      .then((items) => {
        if (cancelled) return;
        const match = (Array.isArray(items) ? items : []).find(
          (item) => String(item?.doc_id || '') === currentKbDocId
        );
        setRetentionRecord(match || null);
      })
      .catch((requestError) => {
        if (cancelled) return;
        setRetentionError(
          normalizeError(requestError?.message, resolvedText.retentionLoadError, mapErrorMessage)
        );
      })
      .finally(() => {
        if (cancelled) return;
        setRetentionLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [currentKbDocId, currentRevision?.status, enableRetention, mapErrorMessage, resolvedText.retentionLoadError]);

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
    if (!String(documentForm.product_name || '').trim()) {
      setError(
        normalizeError('product_name_required', resolvedText.createDocumentError, mapErrorMessage)
      );
      return null;
    }
    if (!String(documentForm.file_subtype || '').trim()) {
      setError(
        normalizeError('document_control_matrix_file_subtype_required', resolvedText.createDocumentError, mapErrorMessage)
      );
      return null;
    }
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

  const startWorkflowAction = useCallback((action, controlledRevisionId) => {
    setWorkflowAction(String(action || ''));
    setWorkflowActionRevisionId(String(controlledRevisionId || ''));
  }, []);

  const stopWorkflowAction = useCallback(() => {
    setWorkflowAction('');
    setWorkflowActionRevisionId('');
  }, []);

  const commitWorkflowDocument = useCallback(
    async ({ document, successMessage }) => {
      setSelectedDocument(document);
      setSuccess(successMessage);
      await loadDocuments({
        nextFilters: filters,
        preferredDocumentId: String(document.controlled_document_id || ''),
        preferredDocument: document,
        clearMessages: false,
      });
      return document;
    },
    [filters, loadDocuments]
  );

  const handleSubmitRevisionForApproval = useCallback(
    async (controlledRevisionId, { note } = {}) => {
      resetMessages();
      if (matrixPreviewError) {
        setError(matrixPreviewError);
        return null;
      }
      startWorkflowAction('submit', controlledRevisionId);
      try {
        const document = await documentControlApi.submitRevisionForApproval(controlledRevisionId, {
          note: note ?? null,
        });
        return await commitWorkflowDocument({
          document,
          successMessage: resolvedText.submitApprovalSuccess,
        });
      } catch (requestError) {
        setError(
          normalizeError(requestError?.message, resolvedText.submitApprovalError, mapErrorMessage)
        );
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      commitWorkflowDocument,
      mapErrorMessage,
      matrixPreviewError,
      resetMessages,
      resolvedText.submitApprovalError,
      resolvedText.submitApprovalSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleApproveRevisionStep = useCallback(
    async (controlledRevisionId, { note } = {}) => {
      resetMessages();
      startWorkflowAction('approve', controlledRevisionId);
      try {
        const document = await documentControlApi.approveRevisionStep(controlledRevisionId, {
          note: note ?? null,
        });
        return await commitWorkflowDocument({
          document,
          successMessage: resolvedText.approveStepSuccess,
        });
      } catch (requestError) {
        setError(normalizeError(requestError?.message, resolvedText.approveStepError, mapErrorMessage));
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      commitWorkflowDocument,
      mapErrorMessage,
      resetMessages,
      resolvedText.approveStepError,
      resolvedText.approveStepSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleRejectRevisionStep = useCallback(
    async (controlledRevisionId, { note } = {}) => {
      resetMessages();
      startWorkflowAction('reject', controlledRevisionId);
      try {
        const document = await documentControlApi.rejectRevisionStep(controlledRevisionId, {
          note: note ?? null,
        });
        return await commitWorkflowDocument({
          document,
          successMessage: resolvedText.rejectStepSuccess,
        });
      } catch (requestError) {
        setError(normalizeError(requestError?.message, resolvedText.rejectStepError, mapErrorMessage));
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      commitWorkflowDocument,
      mapErrorMessage,
      resetMessages,
      resolvedText.rejectStepError,
      resolvedText.rejectStepSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleAddSignRevisionStep = useCallback(
    async (controlledRevisionId, { approverUserId, note } = {}) => {
      resetMessages();
      const normalizedApproverUserId = String(approverUserId || '').trim();
      if (!normalizedApproverUserId) {
        setError(normalizeError('approver_user_id_required', '', mapErrorMessage));
        return null;
      }
      startWorkflowAction('add_sign', controlledRevisionId);
      try {
        const document = await documentControlApi.addSignRevisionStep(controlledRevisionId, {
          approver_user_id: normalizedApproverUserId,
          note: note ?? null,
        });
        return await commitWorkflowDocument({
          document,
          successMessage: resolvedText.addSignSuccess,
        });
      } catch (requestError) {
        setError(normalizeError(requestError?.message, resolvedText.addSignError, mapErrorMessage));
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      commitWorkflowDocument,
      mapErrorMessage,
      resetMessages,
      resolvedText.addSignError,
      resolvedText.addSignSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleRemindOverdueApprovalStep = useCallback(
    async (controlledRevisionId, { note } = {}) => {
      resetMessages();
      startWorkflowAction('approval_remind', controlledRevisionId);
      try {
        const result = await documentControlApi.remindOverdueApprovalStep(controlledRevisionId, {
          note: note ?? null,
        });
        setSuccess(resolvedText.remindApprovalSuccess);
        return result;
      } catch (requestError) {
        setError(normalizeError(requestError?.message, resolvedText.remindApprovalError, mapErrorMessage));
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      mapErrorMessage,
      resetMessages,
      resolvedText.remindApprovalError,
      resolvedText.remindApprovalSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleGenerateTrainingAssignments = useCallback(
    async (controlledRevisionId, { assigneeUserIds, departmentIds, minReadMinutes = 15, note } = {}) => {
      resetMessages();
      const cleanRevisionId = String(controlledRevisionId || '').trim();
      const normalizedAssignees = (Array.isArray(assigneeUserIds) ? assigneeUserIds : [])
        .map((item) => String(item || '').trim())
        .filter((item) => item.length > 0);
      const normalizedDepartmentIds = (Array.isArray(departmentIds) ? departmentIds : [])
        .map((item) => Number(item))
        .filter((item) => Number.isInteger(item) && item > 0);

      if (!cleanRevisionId) {
        setError(
          normalizeError('controlled_revision_id_required', resolvedText.trainingGenerateError, mapErrorMessage)
        );
        return null;
      }
      if (normalizedAssignees.length === 0 && normalizedDepartmentIds.length === 0) {
        setError(
          normalizeError('training_assignment_assignees_required', resolvedText.trainingGenerateError, mapErrorMessage)
        );
        return null;
      }

      const minutes = Number(minReadMinutes);
      if (!Number.isFinite(minutes) || minutes <= 0) {
        setError(normalizeError('min_read_minutes_invalid', resolvedText.trainingGenerateError, mapErrorMessage));
        return null;
      }
      const resolvedMinutes = Math.floor(minutes);

      setTrainingGenerateLoading(true);
      try {
        const items = await trainingComplianceApi.generateAssignments({
          controlled_revision_id: cleanRevisionId,
          assignee_user_ids: normalizedAssignees,
          department_ids: normalizedDepartmentIds,
          min_read_minutes: resolvedMinutes,
          note: note ?? null,
        });
        setGeneratedTrainingAssignments(items);
        const nextGate = await trainingComplianceApi.getRevisionGate(cleanRevisionId);
        setTrainingGate(nextGate);
        setSuccess(
          `${resolvedText.trainingGenerateSuccess} (${Array.isArray(items) ? items.length : 0})`
        );
        return items;
      } catch (requestError) {
        setError(
          normalizeError(requestError?.message, resolvedText.trainingGenerateError, mapErrorMessage)
        );
        return null;
      } finally {
        setTrainingGenerateLoading(false);
      }
    },
    [
      mapErrorMessage,
      resetMessages,
      resolvedText.trainingGenerateError,
      resolvedText.trainingGenerateSuccess,
    ]
  );

  const handleSetTrainingGate = useCallback(
    async (controlledRevisionId, { trainingRequired, departmentIds } = {}) => {
      resetMessages();
      startWorkflowAction('training_gate', controlledRevisionId);
      try {
        const gate = await trainingComplianceApi.upsertRevisionGate(controlledRevisionId, {
          training_required: Boolean(trainingRequired),
          department_ids: (Array.isArray(departmentIds) ? departmentIds : [])
            .map((item) => Number(item))
            .filter((item) => Number.isInteger(item) && item > 0),
        });
        setTrainingGate(gate);
        setSuccess(resolvedText.trainingGateSaveSuccess);
        return gate;
      } catch (requestError) {
        setError(
          normalizeError(requestError?.message, resolvedText.trainingGateSaveError, mapErrorMessage)
        );
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      mapErrorMessage,
      resetMessages,
      resolvedText.trainingGateSaveError,
      resolvedText.trainingGateSaveSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleSetDistributionDepartments = useCallback(
    async (controlledDocumentId, { departmentIds } = {}) => {
      resetMessages();
      const cleanDocumentId = String(controlledDocumentId || '').trim();
      const normalizedDepartmentIds = (Array.isArray(departmentIds) ? departmentIds : [])
        .map((item) => Number(item))
        .filter((item) => Number.isInteger(item) && item > 0);
      if (!cleanDocumentId) {
        setError(normalizeError('controlled_document_id_required', resolvedText.distributionSaveError, mapErrorMessage));
        return null;
      }
      startWorkflowAction('set_distribution', cleanDocumentId);
      try {
        const items = await documentControlApi.setDistributionDepartments(cleanDocumentId, {
          department_ids: normalizedDepartmentIds,
        });
        setDistributionDepartmentIds(Array.isArray(items) ? items : []);
        setSuccess(resolvedText.distributionSaveSuccess);
        return items;
      } catch (requestError) {
        setError(normalizeError(requestError?.message, resolvedText.distributionSaveError, mapErrorMessage));
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      mapErrorMessage,
      resetMessages,
      resolvedText.distributionSaveError,
      resolvedText.distributionSaveSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handlePublishRevision = useCallback(
    async (controlledRevisionId, { releaseMode, note } = {}) => {
      resetMessages();
      startWorkflowAction('publish', controlledRevisionId);
      try {
        const document = await documentControlApi.publishRevision(controlledRevisionId, {
          release_mode: releaseMode,
          note: note ?? null,
        });
        await loadDepartmentAcks(controlledRevisionId);
        return await commitWorkflowDocument({
          document,
          successMessage: resolvedText.publishSuccess,
        });
      } catch (requestError) {
        setError(normalizeError(requestError?.message, resolvedText.publishError, mapErrorMessage));
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      commitWorkflowDocument,
      loadDepartmentAcks,
      mapErrorMessage,
      resetMessages,
      resolvedText.publishError,
      resolvedText.publishSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleCompleteManualReleaseArchive = useCallback(
    async (controlledRevisionId, { note } = {}) => {
      resetMessages();
      startWorkflowAction('manual_release_complete', controlledRevisionId);
      try {
        const document = await documentControlApi.completeManualReleaseArchive(controlledRevisionId, {
          note: note ?? null,
        });
        await loadDepartmentAcks(controlledRevisionId);
        return await commitWorkflowDocument({
          document,
          successMessage: resolvedText.manualReleaseCompleteSuccess,
        });
      } catch (requestError) {
        setError(
          normalizeError(requestError?.message, resolvedText.manualReleaseCompleteError, mapErrorMessage)
        );
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      commitWorkflowDocument,
      loadDepartmentAcks,
      mapErrorMessage,
      resetMessages,
      resolvedText.manualReleaseCompleteError,
      resolvedText.manualReleaseCompleteSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleConfirmDepartmentAck = useCallback(
    async (controlledRevisionId, departmentId, { notes } = {}) => {
      resetMessages();
      startWorkflowAction('department_ack_confirm', `${controlledRevisionId}:${departmentId}`);
      try {
        const ack = await documentControlApi.confirmRevisionDepartmentAck(controlledRevisionId, departmentId, {
          notes: notes ?? null,
        });
        await loadDepartmentAcks(controlledRevisionId);
        setSuccess(resolvedText.departmentAckConfirmSuccess);
        return ack;
      } catch (requestError) {
        setError(
          normalizeError(requestError?.message, resolvedText.departmentAckConfirmError, mapErrorMessage)
        );
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      loadDepartmentAcks,
      mapErrorMessage,
      resetMessages,
      resolvedText.departmentAckConfirmError,
      resolvedText.departmentAckConfirmSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleRemindOverdueDepartmentAcks = useCallback(
    async (controlledRevisionId, { note } = {}) => {
      resetMessages();
      startWorkflowAction('department_ack_remind', controlledRevisionId);
      try {
        const result = await documentControlApi.remindOverdueRevisionDepartmentAcks(controlledRevisionId, {
          note: note ?? null,
        });
        await loadDepartmentAcks(controlledRevisionId);
        setSuccess(resolvedText.departmentAckRemindSuccess);
        return result;
      } catch (requestError) {
        setError(
          normalizeError(requestError?.message, resolvedText.departmentAckRemindError, mapErrorMessage)
        );
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      loadDepartmentAcks,
      mapErrorMessage,
      resetMessages,
      resolvedText.departmentAckRemindError,
      resolvedText.departmentAckRemindSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleInitiateObsolete = useCallback(
    async (controlledRevisionId, { retirementReason, retentionUntilMs, note } = {}) => {
      resetMessages();
      startWorkflowAction('obsolete_initiate', controlledRevisionId);
      try {
        const document = await documentControlApi.initiateObsoleteRevision(controlledRevisionId, {
          retirement_reason: retirementReason,
          retention_until_ms: retentionUntilMs,
          note: note ?? null,
        });
        return await commitWorkflowDocument({
          document,
          successMessage: resolvedText.obsoleteInitiateSuccess,
        });
      } catch (requestError) {
        setError(
          normalizeError(requestError?.message, resolvedText.obsoleteInitiateError, mapErrorMessage)
        );
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      commitWorkflowDocument,
      mapErrorMessage,
      resetMessages,
      resolvedText.obsoleteInitiateError,
      resolvedText.obsoleteInitiateSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleApproveObsolete = useCallback(
    async (controlledRevisionId, { note } = {}) => {
      resetMessages();
      startWorkflowAction('obsolete_approve', controlledRevisionId);
      try {
        const document = await documentControlApi.approveObsoleteRevision(controlledRevisionId, {
          note: note ?? null,
        });
        return await commitWorkflowDocument({
          document,
          successMessage: resolvedText.obsoleteApproveSuccess,
        });
      } catch (requestError) {
        setError(
          normalizeError(requestError?.message, resolvedText.obsoleteApproveError, mapErrorMessage)
        );
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      commitWorkflowDocument,
      mapErrorMessage,
      resetMessages,
      resolvedText.obsoleteApproveError,
      resolvedText.obsoleteApproveSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  const handleConfirmDestruction = useCallback(
    async (controlledRevisionId, { destructionNotes } = {}) => {
      resetMessages();
      startWorkflowAction('destruction_confirm', controlledRevisionId);
      try {
        const document = await documentControlApi.confirmRevisionDestruction(controlledRevisionId, {
          destruction_notes: destructionNotes,
        });
        return await commitWorkflowDocument({
          document,
          successMessage: resolvedText.destructionConfirmSuccess,
        });
      } catch (requestError) {
        setError(
          normalizeError(requestError?.message, resolvedText.destructionConfirmError, mapErrorMessage)
        );
        return null;
      } finally {
        stopWorkflowAction();
      }
    },
    [
      commitWorkflowDocument,
      mapErrorMessage,
      resetMessages,
      resolvedText.destructionConfirmError,
      resolvedText.destructionConfirmSuccess,
      startWorkflowAction,
      stopWorkflowAction,
    ]
  );

  return {
    loading,
    detailLoading,
    savingDocument,
    savingRevision,
    workflowAction,
    workflowActionRevisionId,
    approvalDetailLoading,
    approvalDetail,
    approvalDetailError,
    fileSubtypeOptions,
    fileSubtypeOptionsError,
    matrixPreviewLoading,
    matrixPreview,
    matrixPreviewError,
    trainingLoading,
    trainingGateLoading,
    trainingGate,
    trainingGateError,
    trainingAssignments,
    trainingError,
    trainingGenerateLoading,
    generatedTrainingAssignments,
    distributionDepartmentsLoading,
    distributionDepartmentIds,
    distributionDepartmentsError,
    departmentAcksLoading,
    departmentAcks,
    departmentAcksError,
    retentionLoading,
    retentionRecord,
    retentionError,
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
    handleSubmitRevisionForApproval,
    handleApproveRevisionStep,
    handleRejectRevisionStep,
    handleRemindOverdueApprovalStep,
    handleAddSignRevisionStep,
    handleSetTrainingGate,
    handleGenerateTrainingAssignments,
    handleSetDistributionDepartments,
    handlePublishRevision,
    handleCompleteManualReleaseArchive,
    handleConfirmDepartmentAck,
    handleRemindOverdueDepartmentAcks,
    handleInitiateObsolete,
    handleApproveObsolete,
    handleConfirmDestruction,
  };
}
