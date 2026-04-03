import { useCallback, useRef, useState } from 'react';
import authClient from '../../api/authClient';
import documentClient, { DOCUMENT_SOURCE } from '../../shared/documents/documentClient';
import { reviewApi } from './api';
import {
  buildApproveBatchSummary,
  buildBatchSummaryText,
  buildRejectBatchSummary,
  collectConflictChecks,
} from './documentReviewUtils';

const SIGNATURE_CANCELLED = '__signature_cancelled__';

export function useDocumentReviewActions({
  activeDocMap,
  documents,
  refreshDocuments,
  setError,
}) {
  const [actionLoading, setActionLoading] = useState(null);
  const [selectedDocIds, setSelectedDocIds] = useState(new Set());
  const [downloadLoading, setDownloadLoading] = useState(null);
  const [batchDownloadLoading, setBatchDownloadLoading] = useState(false);
  const [batchReviewLoading, setBatchReviewLoading] = useState(null);
  const [batchReviewSummary, setBatchReviewSummary] = useState(null);
  const [batchSummaryExpanded, setBatchSummaryExpanded] = useState(false);
  const [batchSummaryCopied, setBatchSummaryCopied] = useState(false);
  const [overwritePrompt, setOverwritePrompt] = useState(null);
  const [signaturePrompt, setSignaturePrompt] = useState(null);
  const [signatureSubmitting, setSignatureSubmitting] = useState(false);
  const [signatureError, setSignatureError] = useState(null);
  const signatureResolverRef = useRef(null);

  const resetBatchFeedback = useCallback(() => {
    setBatchReviewSummary(null);
    setBatchSummaryExpanded(false);
    setBatchSummaryCopied(false);
  }, []);

  const resetSignaturePrompt = useCallback(() => {
    setSignaturePrompt(null);
    setSignatureSubmitting(false);
    setSignatureError(null);
  }, []);

  const requestSignature = useCallback((prompt) => new Promise((resolve, reject) => {
    signatureResolverRef.current = { resolve, reject };
    setSignatureError(null);
    setSignatureSubmitting(false);
    setSignaturePrompt(prompt);
  }), []);

  const closeSignaturePrompt = useCallback(() => {
    const resolver = signatureResolverRef.current;
    signatureResolverRef.current = null;
    resetSignaturePrompt();
    if (resolver) {
      resolver.reject(new Error(SIGNATURE_CANCELLED));
    }
  }, [resetSignaturePrompt]);

  const submitSignaturePrompt = useCallback(async ({ password, signatureMeaning, signatureReason }) => {
    const resolver = signatureResolverRef.current;
    if (!resolver) {
      return;
    }

    setSignatureSubmitting(true);
    setSignatureError(null);
    try {
      const challenge = await authClient.requestSignatureChallenge(password);
      signatureResolverRef.current = null;
      resetSignaturePrompt();
      resolver.resolve({
        sign_token: challenge.sign_token,
        signature_meaning: signatureMeaning,
        signature_reason: signatureReason,
        review_notes: signatureReason,
      });
    } catch (err) {
      setSignatureSubmitting(false);
      setSignatureError(err.message);
    }
  }, [resetSignaturePrompt]);

  const promptSignature = useCallback(async (prompt) => {
    try {
      return await requestSignature(prompt);
    } catch (err) {
      if (err?.message === SIGNATURE_CANCELLED) {
        return null;
      }
      throw err;
    }
  }, [requestSignature]);

  const buildPromptForDoc = useCallback((docId, options) => {
    const filename = activeDocMap.get(docId)?.filename || docId;
    return {
      title: options.title,
      description: `${options.descriptionPrefix}: ${filename}`,
      confirmLabel: options.confirmLabel,
      defaultMeaning: options.defaultMeaning,
      defaultReason: options.defaultReason,
    };
  }, [activeDocMap]);

  const handleApprove = useCallback(async (docId) => {
    setError(null);
    setActionLoading(docId);
    try {
      const conflict = await reviewApi.getConflict(docId);
      if (conflict?.conflict && conflict?.existing) {
        setOverwritePrompt({
          newDocId: docId,
          oldDoc: conflict.existing,
          normalized: conflict.normalized_name,
        });
        return;
      }

      const signaturePayload = await promptSignature(buildPromptForDoc(docId, {
        title: 'Electronic Signature',
        descriptionPrefix: 'Approve document',
        confirmLabel: 'Sign and approve',
        defaultMeaning: 'Document approval',
        defaultReason: 'Approved after review',
      }));
      if (!signaturePayload) return;

      await reviewApi.approve(docId, signaturePayload);
      await refreshDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }, [buildPromptForDoc, promptSignature, refreshDocuments, setError]);

  const handleOverwriteUseNew = useCallback(async () => {
    if (!overwritePrompt) return;
    const { newDocId, oldDoc } = overwritePrompt;

    const signaturePayload = await promptSignature({
      title: 'Electronic Signature',
      description: `Approve overwrite: replace ${oldDoc.filename} with ${activeDocMap.get(newDocId)?.filename || newDocId}`,
      confirmLabel: 'Sign and overwrite',
      defaultMeaning: 'Document supersede approval',
      defaultReason: `Approve overwrite for ${oldDoc.filename}`,
    });
    if (!signaturePayload) return;

    setActionLoading(newDocId);
    setError(null);
    try {
      await reviewApi.approveOverwrite(newDocId, oldDoc.doc_id, signaturePayload);
      setOverwritePrompt(null);
      await refreshDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }, [activeDocMap, overwritePrompt, promptSignature, refreshDocuments, setError]);

  const handleOverwriteKeepOld = useCallback(async () => {
    if (!overwritePrompt) return;
    const { newDocId, oldDoc } = overwritePrompt;

    const signaturePayload = await promptSignature({
      title: 'Electronic Signature',
      description: `Reject new upload and keep approved document ${oldDoc.filename}`,
      confirmLabel: 'Sign and reject',
      defaultMeaning: 'Document rejection',
      defaultReason: 'Keep approved document and reject conflicting upload',
    });
    if (!signaturePayload) return;

    setActionLoading(newDocId);
    setError(null);
    try {
      await reviewApi.reject(newDocId, signaturePayload);
      setOverwritePrompt(null);
      await refreshDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }, [overwritePrompt, promptSignature, refreshDocuments, setError]);

  const handleReject = useCallback(async (docId) => {
    const signaturePayload = await promptSignature(buildPromptForDoc(docId, {
      title: 'Electronic Signature',
      descriptionPrefix: 'Reject document',
      confirmLabel: 'Sign and reject',
      defaultMeaning: 'Document rejection',
      defaultReason: 'Rejected during review',
    }));
    if (!signaturePayload) return;

    setActionLoading(docId);
    try {
      await reviewApi.reject(docId, signaturePayload);
      await refreshDocuments();
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }, [buildPromptForDoc, promptSignature, refreshDocuments, setError]);

  const handleDelete = useCallback(async (docId) => {
    if (!window.confirm('Delete this document permanently?')) return;

    setActionLoading(docId);
    try {
      const request = await documentClient.delete({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
      await refreshDocuments();
      window.alert(`删除申请已提交${request?.request_id ? `：${request.request_id}` : ''}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setActionLoading(null);
    }
  }, [refreshDocuments, setError]);

  const handleDownload = useCallback(async (docId) => {
    setDownloadLoading(docId);
    try {
      await documentClient.downloadToBrowser({ source: DOCUMENT_SOURCE.KNOWLEDGE, docId });
    } catch (err) {
      setError(err.message);
    } finally {
      setDownloadLoading(null);
    }
  }, [setError]);

  const handleSelectDoc = useCallback((docId) => {
    setSelectedDocIds((prev) => {
      const next = new Set(prev);
      if (next.has(docId)) {
        next.delete(docId);
      } else {
        next.add(docId);
      }
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedDocIds((prev) => (
      prev.size === documents.length ? new Set() : new Set(documents.map((doc) => doc.doc_id))
    ));
  }, [documents]);

  const handleBatchDownload = useCallback(async () => {
    if (selectedDocIds.size === 0) {
      setError('Select at least one document to download.');
      return;
    }

    setBatchDownloadLoading(true);
    try {
      await documentClient.batchDownloadKnowledgeToBrowser(Array.from(selectedDocIds));
      setSelectedDocIds(new Set());
    } catch (err) {
      setError(err.message);
    } finally {
      setBatchDownloadLoading(false);
    }
  }, [selectedDocIds, setError]);

  const handleBatchApproveAll = useCallback(async () => {
    if (documents.length === 0) {
      setError('No pending documents to approve.');
      return;
    }

    setBatchReviewLoading('approve');
    resetBatchFeedback();
    setError(null);
    try {
      const conflictChecks = await collectConflictChecks(documents, reviewApi);
      const conflicted = conflictChecks.filter((item) => item.conflict?.conflict && item.conflict?.existing);
      const conflictCheckFailed = conflictChecks.filter((item) => item.conflictError);
      const approvableDocs = conflictChecks
        .filter((item) => !item.conflictError && !(item.conflict?.conflict && item.conflict?.existing))
        .map((item) => item.doc);

      if (approvableDocs.length === 0) {
        const firstConflict = conflicted[0]?.doc?.filename || conflictCheckFailed[0]?.doc?.filename || '';
        setBatchReviewSummary(
          buildApproveBatchSummary(conflictChecks, {
            success_count: 0,
            failed_count: 0,
            failed_items: [],
          }),
        );
        setError(`Batch approve skipped. conflicts=${conflicted.length}, conflict_checks_failed=${conflictCheckFailed.length}${firstConflict ? `, first=${firstConflict}` : ''}`);
        return;
      }

      const signaturePayload = await promptSignature({
        title: 'Electronic Signature',
        description: `Approve ${approvableDocs.length} documents in batch`,
        confirmLabel: 'Sign and approve batch',
        defaultMeaning: 'Batch document approval',
        defaultReason: `Approved ${approvableDocs.length} documents in batch`,
      });
      if (!signaturePayload) return;

      const result = await reviewApi.approveBatch(
        approvableDocs.map((doc) => doc.doc_id),
        signaturePayload,
      );
      setBatchReviewSummary(buildApproveBatchSummary(conflictChecks, result));
      await refreshDocuments();
      setSelectedDocIds(new Set());

      if (result.failed_count > 0 || conflicted.length > 0 || conflictCheckFailed.length > 0) {
        const firstFailure = result.failed_items?.[0];
        const firstConflict = conflicted[0]?.doc?.filename || conflictCheckFailed[0]?.doc?.filename || '';
        setError(`Batch approve completed. success=${result.success_count}, failed=${result.failed_count}, conflicts=${conflicted.length}, conflict_checks_failed=${conflictCheckFailed.length}${firstFailure ? `, first_failure=${firstFailure.doc_id}:${firstFailure.detail}` : firstConflict ? `, first_conflict=${firstConflict}` : ''}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBatchReviewLoading(null);
    }
  }, [documents, promptSignature, refreshDocuments, resetBatchFeedback, setError]);

  const handleBatchRejectAll = useCallback(async () => {
    if (documents.length === 0) {
      setError('No pending documents to reject.');
      return;
    }

    setBatchReviewLoading('reject');
    resetBatchFeedback();
    setError(null);
    try {
      const signaturePayload = await promptSignature({
        title: 'Electronic Signature',
        description: `Reject ${documents.length} documents in batch`,
        confirmLabel: 'Sign and reject batch',
        defaultMeaning: 'Batch document rejection',
        defaultReason: `Rejected ${documents.length} documents in batch`,
      });
      if (!signaturePayload) return;

      const result = await reviewApi.rejectBatch(
        documents.map((doc) => doc.doc_id),
        signaturePayload,
      );
      setBatchReviewSummary(buildRejectBatchSummary(result));
      await refreshDocuments();
      setSelectedDocIds(new Set());
      if (result.failed_count > 0) {
        const firstFailure = result.failed_items?.[0];
        setError(`Batch reject completed. success=${result.success_count}, failed=${result.failed_count}${firstFailure ? `, first_failure=${firstFailure.doc_id}:${firstFailure.detail}` : ''}`);
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBatchReviewLoading(null);
    }
  }, [documents, promptSignature, refreshDocuments, resetBatchFeedback, setError]);

  const handleCopyBatchSummary = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(buildBatchSummaryText(batchReviewSummary));
      setBatchSummaryCopied(true);
      window.setTimeout(() => setBatchSummaryCopied(false), 1500);
    } catch (err) {
      setError(err.message || 'Failed to copy summary.');
    }
  }, [batchReviewSummary, setError]);

  return {
    actionLoading,
    batchDownloadLoading,
    batchReviewLoading,
    batchReviewSummary,
    batchSummaryCopied,
    batchSummaryExpanded,
    closeSignaturePrompt,
    downloadLoading,
    handleApprove,
    handleBatchApproveAll,
    handleBatchDownload,
    handleBatchRejectAll,
    handleCopyBatchSummary,
    handleDelete,
    handleDownload,
    handleOverwriteKeepOld,
    handleOverwriteUseNew,
    handleReject,
    handleSelectAll,
    handleSelectDoc,
    overwritePrompt,
    selectedDocIds,
    setBatchSummaryExpanded,
    setOverwritePrompt,
    signatureError,
    signaturePrompt,
    signatureSubmitting,
    submitSignaturePrompt,
  };
}
