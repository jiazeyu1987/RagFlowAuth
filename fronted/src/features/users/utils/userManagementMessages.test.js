import {
  DELETE_USER_CONFIRM_MESSAGE,
  ORG_NO_COMPANY_MESSAGE,
  ORG_NO_DEPARTMENT_MESSAGE,
  ROOT_DIRECTORY_COMPANY_REQUIRED_MESSAGE,
  ROOT_DIRECTORY_NAME_REQUIRED_MESSAGE,
  getResetPasswordValidationMessage,
  mapUserManagementErrorMessage,
} from './userManagementMessages';

describe('userManagementMessages', () => {
  it('exposes stable organization and root-directory messages', () => {
    expect(ORG_NO_COMPANY_MESSAGE).toBe('\u7ec4\u7ec7\u7ba1\u7406\u4e2d\u6ca1\u6709\u53ef\u7528\u516c\u53f8\uff0c\u65e0\u6cd5\u521b\u5efa\u6216\u7f16\u8f91\u7528\u6237');
    expect(ORG_NO_DEPARTMENT_MESSAGE).toBe('\u7ec4\u7ec7\u7ba1\u7406\u4e2d\u6ca1\u6709\u53ef\u7528\u90e8\u95e8\uff0c\u65e0\u6cd5\u521b\u5efa\u6216\u7f16\u8f91\u7528\u6237');
    expect(ROOT_DIRECTORY_COMPANY_REQUIRED_MESSAGE).toBe('\u8bf7\u5148\u9009\u62e9\u516c\u53f8');
    expect(ROOT_DIRECTORY_NAME_REQUIRED_MESSAGE).toBe('\u8bf7\u8f93\u5165\u9876\u7ea7\u76ee\u5f55\u540d\u79f0');
    expect(DELETE_USER_CONFIRM_MESSAGE).toBe('\u786e\u5b9a\u8981\u5220\u9664\u8be5\u7528\u6237\u5417\uff1f');
  });

  it('maps known backend error codes into stable UI messages', () => {
    expect(mapUserManagementErrorMessage('managed_kb_root_node_not_found')).toContain(
      '\u5f53\u524d\u8d1f\u8d23\u76ee\u5f55\u5df2\u5931\u6548'
    );
    expect(mapUserManagementErrorMessage('managed_kb_root_node_required_for_sub_admin')).toBe(
      '\u8bf7\u9009\u62e9\u5b50\u7ba1\u7406\u5458\u8d1f\u8d23\u7684\u77e5\u8bc6\u5e93\u76ee\u5f55'
    );
    expect(mapUserManagementErrorMessage('company_required_for_sub_admin')).toBe(
      '\u5b50\u7ba1\u7406\u5458\u5fc5\u987b\u9009\u62e9\u516c\u53f8'
    );
    expect(mapUserManagementErrorMessage('username_already_exists')).toBe(
      '\u7528\u6237\u8d26\u53f7\u5df2\u5b58\u5728'
    );
    expect(mapUserManagementErrorMessage('employee_user_id_required')).toBe(
      '\u8bf7\u4ece\u59d3\u540d\u4e0b\u62c9\u4e2d\u9009\u62e9\u7ec4\u7ec7\u540c\u4e8b'
    );
    expect(mapUserManagementErrorMessage('employee_user_id_not_found')).toBe(
      '\u9009\u62e9\u7684\u5458\u5de5UserID\u4e0d\u5b58\u5728\u4e8e\u5f53\u524d\u7ec4\u7ec7'
    );
    expect(mapUserManagementErrorMessage('employee_user_id_already_bound')).toBe(
      '\u8be5\u7ec4\u7ec7\u5458\u5de5\u5df2\u7ed1\u5b9a\u5176\u4ed6\u7528\u6237\u8d26\u53f7'
    );
    expect(mapUserManagementErrorMessage('employee_org_profile_mismatch')).toBe(
      '\u63d0\u4ea4\u7684\u59d3\u540d\u6216\u7ec4\u7ec7\u5f52\u5c5e\u4e0e\u5458\u5de5\u6863\u6848\u4e0d\u4e00\u81f4'
    );
    expect(mapUserManagementErrorMessage('default_department_not_found_for_company')).toBe(
      '\u8be5\u5458\u5de5\u5728\u7ec4\u7ec7\u4e2d\u672a\u914d\u7f6e\u90e8\u95e8\uff0c\u4e14\u6240\u5728\u516c\u53f8\u6ca1\u6709\u53ef\u7528\u9ed8\u8ba4\u90e8\u95e8'
    );
    expect(mapUserManagementErrorMessage('unknown_error')).toBe('unknown_error');
    expect(mapUserManagementErrorMessage('')).toBe('');
  });

  it('maps reset-password validation codes', () => {
    expect(getResetPasswordValidationMessage('password_required')).toBe('\u8bf7\u8f93\u5165\u65b0\u5bc6\u7801');
    expect(getResetPasswordValidationMessage('password_mismatch')).toBe(
      '\u4e24\u6b21\u8f93\u5165\u7684\u65b0\u5bc6\u7801\u4e0d\u4e00\u81f4'
    );
    expect(getResetPasswordValidationMessage('other')).toBe('');
  });
});
