import { act, renderHook, waitFor } from '@testing-library/react';

import useTrainingAckPage from './useTrainingAckPage';
import trainingComplianceApi from '../../trainingCompliance/api';

jest.mock('../../trainingCompliance/api', () => ({
  __esModule: true,
  default: {
    listAssignments: jest.fn(),
    listQuestionThreads: jest.fn(),
    listEffectiveRevisions: jest.fn(),
    acknowledgeAssignment: jest.fn(),
    resolveQuestionThread: jest.fn(),
    generateAssignments: jest.fn(),
    recordReadProgress: jest.fn(),
  },
}));

describe('useTrainingAckPage', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
    trainingComplianceApi.listAssignments.mockResolvedValue([
      {
        assignment_id: 'assign-1',
        status: 'pending',
        doc_code: 'DOC-TR-001',
        revision_no: 1,
        assigned_at_ms: 1_770_000_000_000,
        required_read_ms: 60_000,
        read_progress_ms: 0,
        last_read_ping_at_ms: null,
      },
    ]);
    trainingComplianceApi.listQuestionThreads.mockResolvedValue([]);
    trainingComplianceApi.listEffectiveRevisions.mockResolvedValue([]);
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('starts reading and sends heartbeat progress updates', async () => {
    trainingComplianceApi.recordReadProgress
      .mockResolvedValueOnce({
        assignment_id: 'assign-1',
        status: 'pending',
        doc_code: 'DOC-TR-001',
        revision_no: 1,
        assigned_at_ms: 1_770_000_000_000,
        required_read_ms: 60_000,
        read_progress_ms: 0,
        last_read_ping_at_ms: 1_770_000_000_000,
      })
      .mockResolvedValueOnce({
        assignment_id: 'assign-1',
        status: 'pending',
        doc_code: 'DOC-TR-001',
        revision_no: 1,
        assigned_at_ms: 1_770_000_000_000,
        required_read_ms: 60_000,
        read_progress_ms: 5_000,
        last_read_ping_at_ms: 1_770_000_005_000,
      });

    const { result } = renderHook(() => useTrainingAckPage({
      canAssign: false,
      canAcknowledge: true,
      canReviewQuestions: false,
    }));

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.handleStartReading('assign-1');
    });

    expect(trainingComplianceApi.recordReadProgress).toHaveBeenNthCalledWith(1, 'assign-1', {
      event: 'start',
    });
    expect(result.current.trackingAssignmentId).toBe('assign-1');

    await act(async () => {
      jest.advanceTimersByTime(5_000);
    });

    await waitFor(() => expect(trainingComplianceApi.recordReadProgress).toHaveBeenNthCalledWith(2, 'assign-1', {
      event: 'heartbeat',
    }));
    expect(result.current.assignments[0].read_progress_ms).toBe(5_000);
  });
});
