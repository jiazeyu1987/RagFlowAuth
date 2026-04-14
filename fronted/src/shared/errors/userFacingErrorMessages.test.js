import { mapUserFacingErrorMessage } from './userFacingErrorMessages';

describe('mapUserFacingErrorMessage', () => {
  it('maps knowledge management permission errors to the localized UI copy', () => {
    expect(mapUserFacingErrorMessage('no_knowledge_management_permission')).toBe(
      '当前账号没有知识库管理权限'
    );
  });

  it('falls back to the provided message for unknown ascii error codes', () => {
    expect(mapUserFacingErrorMessage('some_unknown_backend_code', 'Load failed.')).toBe('Load failed.');
  });

  it('keeps non-code messages unchanged', () => {
    expect(mapUserFacingErrorMessage('Service is temporarily unavailable.')).toBe('Service is temporarily unavailable.');
  });
});
