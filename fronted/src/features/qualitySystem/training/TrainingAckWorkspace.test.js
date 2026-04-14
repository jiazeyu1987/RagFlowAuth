import React from 'react';
import { act, render, screen } from '@testing-library/react';

import TrainingAckWorkspace from './TrainingAckWorkspace';
import useTrainingAckPage from './useTrainingAckPage';
import { useAuth } from '../../../hooks/useAuth';

jest.mock('./useTrainingAckPage', () => ({
  __esModule: true,
  default: jest.fn(),
}));

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('TrainingAckWorkspace', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.setSystemTime(new Date('2026-04-14T08:00:00Z'));
    useAuth.mockReturnValue({
      can: jest.fn((resource, action) => resource === 'training_ack' && action !== 'review_questions'),
    });
    useTrainingAckPage.mockReturnValue({
      loading: false,
      error: '',
      success: '',
      assignments: [
        {
          assignment_id: 'assign-1',
          doc_code: 'DOC-TR-001',
          revision_no: 1,
          status: 'pending',
          assigned_at_ms: Date.now(),
          required_read_ms: 2_000,
          read_progress_ms: 0,
          last_read_ping_at_ms: Date.now(),
          min_ack_at_ms: Date.now() + 2_000,
        },
      ],
      pendingAssignments: [
        {
          assignment_id: 'assign-1',
          doc_code: 'DOC-TR-001',
          revision_no: 1,
          status: 'pending',
          assigned_at_ms: Date.now(),
          required_read_ms: 2_000,
          read_progress_ms: 0,
          last_read_ping_at_ms: Date.now(),
          min_ack_at_ms: Date.now() + 2_000,
        },
      ],
      questionThreads: [],
      effectiveRevisions: [],
      selectedRevisionId: '',
      questionDrafts: {},
      resolutionDrafts: {},
      busyIds: [],
      generateBusy: false,
      trackingAssignmentId: 'assign-1',
      readHeartbeatMs: 5000,
      setSelectedRevisionId: jest.fn(),
      setQuestionDrafts: jest.fn(),
      setResolutionDrafts: jest.fn(),
      handleStartReading: jest.fn(),
      handleAcknowledge: jest.fn(),
      handleResolveThread: jest.fn(),
      handleGenerateAssignments: jest.fn(),
    });
  });

  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it('shows a countdown and unlocks actions after the minimum read time', () => {
    render(<TrainingAckWorkspace />);

    expect(screen.getByTestId('training-ack-countdown-assign-1')).toHaveTextContent('剩余阅读时间');
    expect(screen.getByRole('button', { name: '已知晓' })).toBeDisabled();
    expect(screen.getByRole('button', { name: '有疑问' })).toBeDisabled();

    act(() => {
      jest.advanceTimersByTime(2_000);
    });

    expect(screen.getByTestId('training-ack-countdown-assign-1')).toHaveTextContent('已达到确认时间');
    expect(screen.getByRole('button', { name: '已知晓' })).toBeEnabled();
    expect(screen.getByRole('button', { name: '有疑问' })).toBeEnabled();
  });
});
