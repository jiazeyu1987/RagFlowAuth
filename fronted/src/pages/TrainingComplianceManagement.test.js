import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TrainingComplianceManagement from './TrainingComplianceManagement';
import authClient from '../api/authClient';
import trainingComplianceApi from '../features/trainingCompliance/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../api/authClient', () => ({
  __esModule: true,
  default: {
    listUsers: jest.fn(),
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

const usersResponse = [
  { user_id: 'user-1', username: 'alice', full_name: 'Alice' },
  { user_id: 'user-2', username: 'bob', full_name: 'Bob' },
];

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

const mockLoaders = () => {
  trainingComplianceApi.listRequirements.mockResolvedValue(requirementsResponse);
  authClient.listUsers.mockResolvedValue(usersResponse);
  trainingComplianceApi.listRecords.mockResolvedValue(recordsResponse);
  trainingComplianceApi.listCertifications.mockResolvedValue(certificationsResponse);
};

describe('TrainingComplianceManagement', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    jest.spyOn(Date, 'now').mockReturnValue(new Date('2026-04-04T09:30:00.000Z').getTime());
    useAuth.mockReturnValue({ user: currentAdmin });
    trainingComplianceApi.createRecord.mockResolvedValue({ record_id: 'record-2' });
    trainingComplianceApi.createCertification.mockResolvedValue({ certification_id: 'cert-2' });
    mockLoaders();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('loads requirements, users, records and certifications for admins', async () => {
    render(<TrainingComplianceManagement />);

    expect(await screen.findByTestId('training-compliance-page')).toBeInTheDocument();
    expect(screen.getByText('培训合规管理')).toBeInTheDocument();
    expect(screen.getAllByText('TR-001').length).toBeGreaterThan(0);
    expect(screen.getAllByText(/Alice/).length).toBeGreaterThan(0);

    await waitFor(() => {
      expect(trainingComplianceApi.listRequirements).toHaveBeenCalledWith({ limit: 100 });
      expect(authClient.listUsers).toHaveBeenCalledWith({ limit: 200 });
      expect(trainingComplianceApi.listRecords).toHaveBeenCalledWith({ limit: 100 });
      expect(trainingComplianceApi.listCertifications).toHaveBeenCalledWith({ limit: 100 });
    });
  });

  it('shows a default training summary, Chinese controlled action labels and one-year valid-until default', async () => {
    render(<TrainingComplianceManagement />);

    const summaryInput = await screen.findByTestId('training-record-summary');
    const certificationValidUntilInput = screen.getByTestId('training-certification-valid-until');

    expect(screen.getAllByText('文档审批').length).toBeGreaterThan(0);
    expect(screen.getAllByRole('option', { name: 'TR-001 | 文档审批 | v2026.04' }).length).toBeGreaterThan(0);
    expect(summaryInput).toHaveValue('已完成《审批与发布操作员培训》培训，满足文档审批上岗要求。');

    const validUntilMs = Date.parse(certificationValidUntilInput.value);
    const nowMs = Date.now();
    expect(validUntilMs - nowMs).toBeGreaterThanOrEqual(364 * 24 * 60 * 60 * 1000);
    expect(validUntilMs - nowMs).toBeLessThanOrEqual(366 * 24 * 60 * 60 * 1000);
  });

  it('submits a training record with admin trainer and reviewer fields', async () => {
    const user = userEvent.setup();

    render(<TrainingComplianceManagement />);

    await screen.findByTestId('training-record-user');

    await user.selectOptions(screen.getByTestId('training-record-user'), 'user-2');
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
          training_outcome: 'passed',
          effectiveness_status: 'effective',
          effectiveness_score: 100,
          effectiveness_summary: '完成岗位培训并通过效果评估',
          training_notes: '现场培训',
          effectiveness_reviewed_by_user_id: 'admin-1',
          completed_at_ms: expect.any(Number),
          effectiveness_reviewed_at_ms: expect.any(Number),
        })
      );
    });

    expect(await screen.findByTestId('training-compliance-success')).toHaveTextContent('培训记录已保存。');
  });

  it('submits an operator certification with the current admin as grantor', async () => {
    const user = userEvent.setup();

    render(<TrainingComplianceManagement />);

    await screen.findByTestId('training-certification-user');

    await user.selectOptions(screen.getByTestId('training-certification-user'), 'user-2');
    await user.clear(screen.getByTestId('training-certification-valid-until'));
    await user.type(screen.getByTestId('training-certification-valid-until'), '2026-12-31T09:30');
    await user.clear(screen.getByTestId('training-certification-notes'));
    await user.type(screen.getByTestId('training-certification-notes'), '授权上岗');
    await user.click(screen.getByTestId('training-certification-submit'));

    await waitFor(() => {
      expect(trainingComplianceApi.createCertification).toHaveBeenCalledWith(
        expect.objectContaining({
          requirement_code: 'TR-001',
          user_id: 'user-2',
          granted_by_user_id: 'admin-1',
          certification_status: 'active',
          certification_notes: '授权上岗',
          valid_until_ms: expect.any(Number),
        })
      );
    });

    expect(await screen.findByTestId('training-compliance-success')).toHaveTextContent('上岗认证已保存。');
  });
});
