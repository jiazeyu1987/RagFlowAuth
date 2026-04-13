import { useCallback, useEffect, useMemo, useState } from 'react';
import trainingComplianceApi from '../../trainingCompliance/api';
import { mapUserFacingErrorMessage } from '../../../shared/errors/userFacingErrorMessages';

const DEFAULT_LOAD_ERROR = '加载培训任务失败';
const DEFAULT_SAVE_ERROR = '培训任务处理失败';
const DEFAULT_RESOLVE_ERROR = '疑问处理失败';
const DEFAULT_GENERATE_ERROR = '生成培训任务失败';

export default function useTrainingAckPage({ canAssign, canAcknowledge, canReviewQuestions }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [assignments, setAssignments] = useState([]);
  const [questionThreads, setQuestionThreads] = useState([]);
  const [effectiveRevisions, setEffectiveRevisions] = useState([]);
  const [selectedRevisionId, setSelectedRevisionId] = useState('');
  const [questionDrafts, setQuestionDrafts] = useState({});
  const [resolutionDrafts, setResolutionDrafts] = useState({});
  const [busyIds, setBusyIds] = useState([]);
  const [generateBusy, setGenerateBusy] = useState(false);

  const setBusy = useCallback((key, active) => {
    setBusyIds((previous) => {
      const set = new Set(previous);
      if (active) set.add(key);
      else set.delete(key);
      return Array.from(set);
    });
  }, []);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const requests = [
        trainingComplianceApi.listAssignments({ limit: 100 }),
      ];
      if (canReviewQuestions || canAcknowledge) {
        requests.push(trainingComplianceApi.listQuestionThreads({ limit: 100 }));
      }
      if (canAssign) {
        requests.push(trainingComplianceApi.listEffectiveRevisions({ limit: 100 }));
      }
      const responses = await Promise.all(requests);
      setAssignments(responses[0] || []);
      if (canReviewQuestions || canAcknowledge) {
        setQuestionThreads(responses[1] || []);
      } else {
        setQuestionThreads([]);
      }
      if (canAssign) {
        const revisions = responses[responses.length - 1] || [];
        setEffectiveRevisions(revisions);
        setSelectedRevisionId((previous) => previous || String(revisions[0]?.controlled_revision_id || ''));
      } else {
        setEffectiveRevisions([]);
        setSelectedRevisionId('');
      }
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, DEFAULT_LOAD_ERROR));
    } finally {
      setLoading(false);
    }
  }, [canAcknowledge, canAssign, canReviewQuestions]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const pendingAssignments = useMemo(
    () => assignments.filter((item) => String(item?.status || '') === 'pending'),
    [assignments]
  );

  const handleAcknowledge = useCallback(async (assignmentId, decision) => {
    setBusy(assignmentId, true);
    setError('');
    setSuccess('');
    try {
      const payload = { decision };
      if (decision === 'questioned') {
        payload.question_text = String(questionDrafts[assignmentId] || '').trim();
      }
      await trainingComplianceApi.acknowledgeAssignment(assignmentId, payload);
      setSuccess(decision === 'acknowledged' ? '已确认知晓' : '疑问已提交');
      setQuestionDrafts((previous) => ({ ...previous, [assignmentId]: '' }));
      await loadData();
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, DEFAULT_SAVE_ERROR));
    } finally {
      setBusy(assignmentId, false);
    }
  }, [loadData, questionDrafts, setBusy]);

  const handleResolveThread = useCallback(async (threadId) => {
    setBusy(threadId, true);
    setError('');
    setSuccess('');
    try {
      await trainingComplianceApi.resolveQuestionThread(threadId, {
        resolution_text: String(resolutionDrafts[threadId] || '').trim(),
      });
      setSuccess('疑问已处理');
      setResolutionDrafts((previous) => ({ ...previous, [threadId]: '' }));
      await loadData();
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, DEFAULT_RESOLVE_ERROR));
    } finally {
      setBusy(threadId, false);
    }
  }, [loadData, resolutionDrafts, setBusy]);

  const handleGenerateAssignments = useCallback(async () => {
    if (!selectedRevisionId) {
      setError('请选择一个生效版本');
      return;
    }
    setGenerateBusy(true);
    setError('');
    setSuccess('');
    try {
      const created = await trainingComplianceApi.generateAssignments({
        controlled_revision_id: selectedRevisionId,
        min_read_minutes: 15,
      });
      setSuccess(`已生成 ${created.length} 条培训任务`);
      await loadData();
    } catch (requestError) {
      setError(mapUserFacingErrorMessage(requestError?.message, DEFAULT_GENERATE_ERROR));
    } finally {
      setGenerateBusy(false);
    }
  }, [loadData, selectedRevisionId]);

  return {
    loading,
    error,
    success,
    assignments,
    pendingAssignments,
    questionThreads,
    effectiveRevisions,
    selectedRevisionId,
    questionDrafts,
    resolutionDrafts,
    busyIds,
    generateBusy,
    setSelectedRevisionId,
    setQuestionDrafts,
    setResolutionDrafts,
    handleAcknowledge,
    handleResolveThread,
    handleGenerateAssignments,
  };
}
