import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import QualitySystemBatchRecords from './QualitySystemBatchRecords';
import batchRecordsApi from '../features/batchRecords/api';
import { electronicSignatureApi } from '../features/electronicSignature/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../features/batchRecords/api', () => ({
  __esModule: true,
  default: {
    listTemplates: jest.fn(),
    publishTemplate: jest.fn(),
    createTemplate: jest.fn(),
    createTemplateVersion: jest.fn(),
    listExecutions: jest.fn(),
    createExecution: jest.fn(),
    getExecution: jest.fn(),
    writeStep: jest.fn(),
    signExecution: jest.fn(),
    reviewExecution: jest.fn(),
    exportExecution: jest.fn(),
  },
}));

jest.mock('../features/electronicSignature/api', () => ({
  __esModule: true,
  electronicSignatureApi: {
    requestSignatureChallenge: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

const renderPage = () => render(
  <MemoryRouter initialEntries={['/quality-system/batch-records']}>
    <QualitySystemBatchRecords />
  </MemoryRouter>
);

describe('QualitySystemBatchRecords', () => {
  beforeEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      can: jest.fn(() => true),
    });

    batchRecordsApi.listTemplates.mockResolvedValue([
      {
        template_id: 'tpl-1',
        template_code: 'BR-TPL-001',
        template_name: 'Production',
        version_no: 1,
        status: 'active',
        updated_at_ms: 10,
      },
    ]);
    batchRecordsApi.listExecutions.mockResolvedValue([
      {
        execution_id: 'exec-1',
        title: 'Execution 1',
        status: 'in_progress',
        batch_no: 'B-0001',
        template_code: 'BR-TPL-001',
        template_version_no: 1,
      },
    ]);
    batchRecordsApi.getExecution.mockResolvedValue({
      bundle: {
        execution: {
          execution_id: 'exec-1',
          status: 'in_progress',
          batch_no: 'B-0001',
          started_at_ms: 1,
        },
        template: {
          template_code: 'BR-TPL-001',
          version_no: 1,
          template_name: 'Production',
          steps: [{ key: 'mix', title: 'Mixing' }],
        },
        latest_steps: {
          mix: {
            payload: { operator: 'op1' },
            created_at_ms: 2,
            created_by_username: 'admin',
          },
        },
        step_entries: [],
      },
      signed_signature: null,
      reviewed_signature: null,
    });
    batchRecordsApi.writeStep.mockResolvedValue({ ok: true });
    batchRecordsApi.signExecution.mockResolvedValue({ ok: true });
    electronicSignatureApi.requestSignatureChallenge.mockResolvedValue({ sign_token: 'tok-1', expires_at_ms: 9999 });
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it('renders template and execution lists', async () => {
    renderPage();

    expect(await screen.findByTestId('quality-system-batch-records-page')).toBeInTheDocument();

    await waitFor(() => {
      expect(batchRecordsApi.listTemplates).toHaveBeenCalled();
      expect(batchRecordsApi.listExecutions).toHaveBeenCalled();
    });

    expect(screen.getAllByText('BR-TPL-001 v1 · Production').length).toBeGreaterThan(0);
  });

  it('writes a step entry', async () => {
    const user = userEvent.setup();
    renderPage();

    fireEvent.click(await screen.findByTestId('batch-records-execution-item-exec-1'));
    await waitFor(() => {
      expect(batchRecordsApi.getExecution).toHaveBeenCalledWith('exec-1');
    });
    expect(await screen.findByTestId('batch-records-step-mix')).toBeInTheDocument();

    const textarea = screen.getByDisplayValue(/operator/);
    await user.clear(textarea);
    fireEvent.change(textarea, { target: { value: '{"operator":"op2","result":"ok"}' } });
    await user.click(screen.getByTestId('batch-records-step-save-mix'));

    await waitFor(() => {
      expect(batchRecordsApi.writeStep).toHaveBeenCalledWith('exec-1', {
        step_key: 'mix',
        payload: { operator: 'op2', result: 'ok' },
      });
    });
  });

  it('merges uploaded photo evidence into the step payload', async () => {
    const user = userEvent.setup();
    renderPage();

    fireEvent.click(await screen.findByTestId('batch-records-execution-item-exec-1'));
    await waitFor(() => {
      expect(batchRecordsApi.getExecution).toHaveBeenCalledWith('exec-1');
    });
    expect(await screen.findByTestId('batch-records-step-mix')).toBeInTheDocument();

    const fileInput = screen.getByTestId('batch-records-step-photo-mix');
    const photoFile = new File(['photo-bytes'], 'mix.jpg', { type: 'image/jpeg' });
    await user.upload(fileInput, photoFile);

    expect(await screen.findByTestId('batch-records-step-photo-pending-mix')).toHaveTextContent('mix.jpg');

    await user.click(screen.getByTestId('batch-records-step-save-mix'));

    await waitFor(() => {
      expect(batchRecordsApi.writeStep).toHaveBeenCalled();
    });
    const [, payload] = batchRecordsApi.writeStep.mock.calls.at(-1);
    expect(payload.step_key).toBe('mix');
    expect(payload.payload.operator).toBe('op1');
    expect(Array.isArray(payload.payload.photo_evidences)).toBe(true);
    expect(payload.payload.photo_evidences[0]).toMatchObject({
      filename: 'mix.jpg',
      media_type: 'image/jpeg',
    });
    expect(String(payload.payload.photo_evidences[0].data_url || '')).toMatch(/^data:image\/jpeg;base64,/);
  });

  it('signs an execution using electronic-signature challenge', async () => {
    const user = userEvent.setup();
    renderPage();

    fireEvent.click(await screen.findByTestId('batch-records-execution-item-exec-1'));
    await waitFor(() => {
      expect(batchRecordsApi.getExecution).toHaveBeenCalledWith('exec-1');
    });
    expect(await screen.findByTestId('batch-records-step-mix')).toBeInTheDocument();

    await user.type(screen.getByPlaceholderText('meaning'), 'Operator sign-off');
    await user.type(screen.getByPlaceholderText('reason'), 'All good');
    await user.type(screen.getByPlaceholderText('电子签名口令'), 'pw');
    await user.click(screen.getByTestId('batch-records-sign'));

    await waitFor(() => {
      expect(electronicSignatureApi.requestSignatureChallenge).toHaveBeenCalledWith('pw');
    });
    await waitFor(() => {
      expect(batchRecordsApi.signExecution).toHaveBeenCalledWith('exec-1', {
        sign_token: 'tok-1',
        meaning: 'Operator sign-off',
        reason: 'All good',
      });
    });
  });
});
