import { mapUserFacingErrorMessage } from './userFacingErrorMessages';

describe('mapUserFacingErrorMessage', () => {
  it('maps knowledge management permission errors to Chinese', () => {
    expect(mapUserFacingErrorMessage('no_knowledge_management_permission')).toBe(
      '当前账号没有知识库管理权限'
    );
  });

  it('falls back to the provided Chinese message for unknown ascii error codes', () => {
    expect(mapUserFacingErrorMessage('some_unknown_backend_code', '加载失败')).toBe('加载失败');
  });

  it('keeps non-code messages unchanged', () => {
    expect(mapUserFacingErrorMessage('服务暂时不可用')).toBe('服务暂时不可用');
  });
});
