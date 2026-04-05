import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TrainingComplianceManagement from './TrainingComplianceManagement';
import trainingComplianceApi from '../features/trainingCompliance/api';
import { usersApi } from '../features/users/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../features/users/api', () => ({
  __esModule: true,
  usersApi: {
    search: jest.fn(),
  },
}));

jest.mock('../features/trainingCompliance/api', () => ({
  __esModule: true,
  default: {
    listRequirements: jest.fn(),
    listRecords: jest.fn(),
    listCertifications: jest.fn(),
    createRecord: jest.fn(),
    createCertification: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
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
      requirement_name: '审批与发布操作员培训',
      controlled_action: 'document_review',
      role_code: '*',
      curriculum_version: 'v2026.04',
      recertification_interval_days: 365,
      active: true,
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

const renderPage = (initialEntries = ['/training-compliance']) => render(
  <MemoryRouter initialEntries={initialEntries}>
    <TrainingComplianceManagement />
  </MemoryRouter>
);

describe('TrainingComplianceManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(Date, 'now').mockReturnValue(new Date('2026-04-04T09:30:00.000Z').getTime());

    useAuth.mockReturnValue({ user: currentAdmin });

    trainingComplianceApi.listRequirements.mockResolvedValue(requirementsResponse);
    trainingComplianceApi.listRecords.mockResolvedValue(recordsResponse);
    trainingComplianceApi.listCertifications.mockResolvedValue(certificationsResponse);
    trainingComplianceApi.createRecord.mockResolvedValue({ record_id: 'record-2' });
    trainingComplianceApi.createCertification.mockResolvedValue({ certification_id: 'cert-2' });

    usersApi.search.mockImplementation(async (keyword) => {
      const normalized = String(keyword || '').trim().toLowerCase();
      return searchUsers.filter((item) => (
        item.user_id.toLowerCase().includes(normalized)
        || item.username.toLowerCase().includes(normalized)
        || item.full_name.toLowerCase().includes(normalized)
      ));
    });
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('loads requirements and recent records without preloading all users', async () => {
    renderPage();

    expect(await screen.findByTestId('training-compliance-page')).toBeInTheDocument();
    expect(screen.getByText('培训合规管理')).toBeInTheDocument();
    expect(screen.getAllByText('TR-001').length).toBeGreaterThan(0);
    expect(screen.getByTestId('training-records-tab-panel')).toBeInTheDocument();

    await waitFor(() => {
      expect(trainingComplianceApi.listRequirements).toHaveBeenCalledWith({ limit: 100 });
      expect(trainingComplianceApi.listRecords).toHaveBeenCalledWith({ limit: 100 });
      expect(trainingComplianceApi.listCertifications).toHaveBeenCalledWith({ limit: 100 });
    });

    expect(usersApi.search).not.toHaveBeenCalled();
  });

  it('switches between training record and certification tabs', async () => {
    const user = userEvent.setup();

    renderPage();

    expect(await screen.findByTestId('training-records-tab-panel')).toBeInTheDocument();
    expect(screen.queryByTestId('training-certifications-tab-panel')).not.toBeInTheDocument();

    await user.click(screen.getByTestId('training-tab-certifications'));

    expect(await screen.findByTestId('training-certifications-tab-panel')).toBeInTheDocument();
    expect(screen.queryByTestId('training-records-tab-panel')).not.toBeInTheDocument();
  });

  it('shows default summary, Chinese controlled action labels and one-year valid-until default', async () => {
    const user = userEvent.setup();

    renderPage();

    const summaryInput = await screen.findByTestId('training-record-summary');
    expect(screen.getAllByText('审批决策').length).toBeGreaterThan(0);
    expect(screen.getAllByRole('option', { name: 'TR-001 | 审批决策 | v2026.04' }).length).toBeGreaterThan(0);
    expect(summaryInput).toHaveValue('已完成《审批与发布操作员培训》培训，满足审批决策上岗要求。');

    await user.click(screen.getByTestId('training-tab-certifications'));
    const certificationValidUntilInput = await screen.findByTestId('training-certification-valid-until');
    const validUntilMs = Date.parse(certificationValidUntilInput.value);
    const nowMs = Date.now();

    expect(validUntilMs - nowMs).toBeGreaterThanOrEqual(364 * 24 * 60 * 60 * 1000);
    expect(validUntilMs - nowMs).toBeLessThanOrEqual(366 * 24 * 60 * 60 * 1000);
  });

  it('searches users by keyword and submits a training record with the selected user', async () => {
    const user = userEvent.setup();

    renderPage();

    const userInput = await screen.findByTestId('training-record-user-search-input');
    await user.type(userInput, 'bob');

    await waitFor(() => {
      expect(usersApi.search).toHaveBeenCalledWith('bob', 20);
    });

    await user.click(await screen.findByTestId('training-record-user-search-result-user-2'));
    expect(screen.getByTestId('training-record-user-search-selected')).toHaveTextContent('Bob');

    await user.clear(screen.getByTestId('training-record-summary'));
    await user.type(screen.getByTestId('training-record-summary'), '完成岗位培训并通过效果评估');
    await user.clear(screen.getByTestId('training-record-notes'));
    await user.type(screen.getByTestId('training-record-notes'), '现场培训');
    await user.click(screen.getByTestId('training-record-submit'));

    await waitFor(() => {
      expect(trainingComplianceApi.createRecord).toHaveBeenCalledWith(
        expect.objectContaining({
          requirement_code: 'TR-001',
          user_id: 'user-2',
          curriculum_version: 'v2026.04',
          trainer_user_id: 'admin-1',
          effectiveness_summary: '完成岗位培训并通过效果评估',
          training_notes: '现场培训',
          effectiveness_reviewed_by_user_id: 'admin-1',
        })
      );
    });

    expect(await screen.findByTestId('training-compliance-success')).toHaveTextContent('培训记录已保存。');
  });

  it('searches users by keyword and submits an operator certification with the selected user', async () => {
    const user = userEvent.setup();

    renderPage();

    await user.click(await screen.findByTestId('training-tab-certifications'));

    const userInput = await screen.findByTestId('training-certification-user-search-input');
    await user.type(userInput, 'alice');

    await waitFor(() => {
      expect(usersApi.search).toHaveBeenCalledWith('alice', 20);
    });

    await user.click(await screen.findByTestId('training-certification-user-search-result-user-1'));
    expect(screen.getByTestId('training-certification-user-search-selected')).toHaveTextContent('Alice');

    await user.clear(screen.getByTestId('training-certification-valid-until'));
    await user.type(screen.getByTestId('training-certification-valid-until'), '2026-12-31T09:30');
    await user.clear(screen.getByTestId('training-certification-notes'));
    await user.type(screen.getByTestId('training-certification-notes'), '授权上岗');
    await user.click(screen.getByTestId('training-certification-submit'));

    await waitFor(() => {
      expect(trainingComplianceApi.createCertification).toHaveBeenCalledWith(
        expect.objectContaining({
          requirement_code: 'TR-001',
          user_id: 'user-1',
          granted_by_user_id: 'admin-1',
          certification_status: 'active',
          certification_notes: '授权上岗',
          valid_until_ms: expect.any(Number),
        })
      );
    });

    expect(await screen.findByTestId('training-compliance-success')).toHaveTextContent('上岗认证已保存。');
  });

  it('prefills tab, target user and requirement from approval-center query params', async () => {
    renderPage(['/training-compliance?tab=certifications&user_id=user-2&controlled_action=document_review']);

    expect(await screen.findByTestId('training-certifications-tab-panel')).toBeInTheDocument();

    await waitFor(() => {
      expect(usersApi.search).toHaveBeenCalledWith('user-2', 20);
    });

    expect(await screen.findByTestId('training-certification-user-search-selected')).toHaveTextContent('Bob');
    expect(screen.getByTestId('training-certification-requirement')).toHaveValue('TR-001');

    await userEvent.setup().click(screen.getByTestId('training-tab-records'));
    expect(await screen.findByTestId('training-record-user-search-selected')).toHaveTextContent('Bob');
    expect(screen.getByTestId('training-record-requirement')).toHaveValue('TR-001');
  });
});
