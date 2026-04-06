import trainingComplianceApi from './api';
import { httpClient } from '../../shared/http/httpClient';

jest.mock('../../config/backend', () => ({
  authBackendUrl: (path) => `http://auth.local${path}`,
}));

jest.mock('../../shared/http/httpClient', () => ({
  httpClient: {
    requestJson: jest.fn(),
  },
}));

describe('trainingComplianceApi', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('normalizes list endpoints to stable arrays and validates create responses', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ items: [{ requirement_code: 'TR-001' }] })
      .mockResolvedValueOnce({ items: [{ record_id: 'record-1' }] })
      .mockResolvedValueOnce({ items: [{ certification_id: 'cert-1' }] })
      .mockResolvedValueOnce({ record: { record_id: 'record-2' } })
      .mockResolvedValueOnce({ certification: { certification_id: 'cert-2' } });

    await expect(
      trainingComplianceApi.listRequirements({
        limit: 50,
        controlledAction: 'document_review',
        roleCode: 'approver',
      })
    ).resolves.toEqual([{ requirement_code: 'TR-001' }]);
    await expect(
      trainingComplianceApi.listRecords({
        limit: 20,
        requirementCode: 'TR-001',
        userId: 'user-1',
      })
    ).resolves.toEqual([{ record_id: 'record-1' }]);
    await expect(
      trainingComplianceApi.listCertifications({
        limit: 10,
        requirementCode: 'TR-001',
        userId: 'user-2',
      })
    ).resolves.toEqual([{ certification_id: 'cert-1' }]);
    await expect(
      trainingComplianceApi.createRecord({ requirement_code: 'TR-001' })
    ).resolves.toEqual({ record_id: 'record-2' });
    await expect(
      trainingComplianceApi.createCertification({ requirement_code: 'TR-001' })
    ).resolves.toEqual({ certification_id: 'cert-2' });

    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      1,
      'http://auth.local/api/training-compliance/requirements?limit=50&controlled_action=document_review&role_code=approver',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      2,
      'http://auth.local/api/training-compliance/records?limit=20&requirement_code=TR-001&user_id=user-1',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      3,
      'http://auth.local/api/training-compliance/certifications?limit=10&requirement_code=TR-001&user_id=user-2',
      { method: 'GET' }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      4,
      'http://auth.local/api/training-compliance/records',
      {
        method: 'POST',
        body: JSON.stringify({ requirement_code: 'TR-001' }),
      }
    );
    expect(httpClient.requestJson).toHaveBeenNthCalledWith(
      5,
      'http://auth.local/api/training-compliance/certifications',
      {
        method: 'POST',
        body: JSON.stringify({ requirement_code: 'TR-001' }),
      }
    );
  });

  it('fails fast when normalized responses do not match the feature contract', async () => {
    httpClient.requestJson
      .mockResolvedValueOnce({ count: 0 })
      .mockResolvedValueOnce({ items: {} })
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce(null)
      .mockResolvedValueOnce({ total: 0 });

    await expect(trainingComplianceApi.listRequirements()).rejects.toThrow(
      'training_compliance_requirements_list_invalid_payload'
    );
    await expect(trainingComplianceApi.listRecords()).rejects.toThrow(
      'training_compliance_records_list_invalid_payload'
    );
    await expect(trainingComplianceApi.createRecord({})).rejects.toThrow(
      'training_compliance_record_create_invalid_payload'
    );
    await expect(trainingComplianceApi.createCertification({})).rejects.toThrow(
      'training_compliance_certification_create_invalid_payload'
    );
    await expect(trainingComplianceApi.listCertifications()).rejects.toThrow(
      'training_compliance_certifications_list_invalid_payload'
    );
  });
});
