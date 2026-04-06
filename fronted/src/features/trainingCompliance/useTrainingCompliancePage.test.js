import { act, renderHook, waitFor } from '@testing-library/react';
import useTrainingCompliancePage from './useTrainingCompliancePage';
import trainingComplianceApi from './api';
import { usersApi } from '../users/api';

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    listRequirements: jest.fn(),
    listRecords: jest.fn(),
    listCertifications: jest.fn(),
    createRecord: jest.fn(),
    createCertification: jest.fn(),
  },
}));

jest.mock('../users/api', () => ({
  __esModule: true,
  usersApi: {
    search: jest.fn(),
  },
}));

const currentAdmin = {
  user_id: 'admin-1',
  username: 'admin',
  full_name: 'Admin User',
  role: 'admin',
};

const requirementsResponse = {
  items: [
    {
      requirement_code: 'TR-001',
      controlled_action: 'document_review',
      curriculum_version: 'v2026.04',
    },
  ],
};

const recordsResponse = {
  items: [
    {
      record_id: 'record-1',
      user_id: 'user-1',
      requirement_code: 'TR-001',
      curriculum_version: 'v2026.04',
      training_outcome: 'passed',
      effectiveness_status: 'effective',
      completed_at_ms: 1712203200000,
    },
  ],
};

const certificationsResponse = {
  items: [
    {
      certification_id: 'cert-1',
      user_id: 'user-1',
      requirement_code: 'TR-001',
      curriculum_version: 'v2026.04',
      certification_status: 'active',
      valid_until_ms: 1743739200000,
      granted_at_ms: 1712203200000,
    },
  ],
};

const searchUsers = [
  { user_id: 'user-1', username: 'alice', full_name: 'Alice' },
  { user_id: 'user-2', username: 'bob', full_name: 'Bob' },
];

const buildDefaultTrainingSummary = (requirement) =>
  requirement ? `summary:${requirement.requirement_code}` : 'summary:default';

const mapErrorMessage = (message, fallback) => message || fallback || 'default-error';

const text = {
  loadError: 'load-error',
  userSearchError: 'user-search-error',
  saveRecordSuccess: 'record-saved',
  saveCertificationSuccess: 'certification-saved',
  saveRecordError: 'save-record-error',
  saveCertificationError: 'save-certification-error',
};

const renderTrainingComplianceHook = (search = '') =>
  renderHook(() =>
    useTrainingCompliancePage({
      user: currentAdmin,
      searchParams: new URLSearchParams(search),
      buildDefaultTrainingSummary,
      mapErrorMessage,
      text,
    })
  );

describe('useTrainingCompliancePage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(Date, 'now').mockReturnValue(new Date('2026-04-04T09:30:00.000Z').getTime());

    trainingComplianceApi.listRequirements.mockResolvedValue(requirementsResponse);
    trainingComplianceApi.listRecords.mockResolvedValue(recordsResponse);
    trainingComplianceApi.listCertifications.mockResolvedValue(certificationsResponse);
    trainingComplianceApi.createRecord.mockResolvedValue({ record_id: 'record-2' });
    trainingComplianceApi.createCertification.mockResolvedValue({ certification_id: 'cert-2' });

    usersApi.search.mockImplementation(async (keyword) => {
      const normalized = String(keyword || '').trim().toLowerCase();
      return searchUsers.filter(
        (item) =>
          item.user_id.toLowerCase().includes(normalized) ||
          item.username.toLowerCase().includes(normalized) ||
          item.full_name.toLowerCase().includes(normalized)
      );
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('loads stable page state and applies query-param prefills through the feature hook', async () => {
    const { result } = renderTrainingComplianceHook(
      'tab=certifications&user_id=user-2&controlled_action=document_review'
    );

    await waitFor(() => expect(result.current.loading).toBe(false));
    await waitFor(() => expect(result.current.activeTab).toBe('certifications'));

    expect(trainingComplianceApi.listRequirements).toHaveBeenCalledWith({ limit: 100 });
    expect(trainingComplianceApi.listRecords).toHaveBeenCalledWith({ limit: 100 });
    expect(trainingComplianceApi.listCertifications).toHaveBeenCalledWith({ limit: 100 });
    expect(usersApi.search).toHaveBeenCalledWith('user-2', 20);
    expect(result.current.recordForm.requirement_code).toBe('TR-001');
    expect(result.current.certificationForm.requirement_code).toBe('TR-001');
    expect(result.current.recordForm.user_id).toBe('user-2');
    expect(result.current.certificationForm.user_id).toBe('user-2');
    expect(result.current.recordUserSearch.keyword).toBe('Bob');
    expect(result.current.certificationUserSearch.keyword).toBe('Bob');
  });

  it('submits a training record with the selected user through the feature hook', async () => {
    const { result } = renderTrainingComplianceHook();

    await waitFor(() => expect(result.current.loading).toBe(false));

    act(() => {
      result.current.handleSelectRecordUser(searchUsers[1]);
      result.current.setRecordForm((previous) => ({
        ...previous,
        effectiveness_summary: 'completed training',
        training_notes: '现场培训',
      }));
    });

    await act(async () => {
      await result.current.handleCreateRecord();
    });

    expect(trainingComplianceApi.createRecord).toHaveBeenCalledWith(
      expect.objectContaining({
        requirement_code: 'TR-001',
        user_id: 'user-2',
        curriculum_version: 'v2026.04',
        trainer_user_id: 'admin-1',
        effectiveness_summary: 'completed training',
        training_notes: '现场培训',
        effectiveness_reviewed_by_user_id: 'admin-1',
      })
    );
    expect(result.current.success).toBe('record-saved');
  });
});
