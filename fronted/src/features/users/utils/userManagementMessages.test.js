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
  it('exposes the fixed organization and root-directory messages', () => {
    expect(ORG_NO_COMPANY_MESSAGE).toBe('组织管理中没有可用公司，无法创建或编辑用户');
    expect(ORG_NO_DEPARTMENT_MESSAGE).toBe('组织管理中没有可用部门，无法创建或编辑用户');
    expect(ROOT_DIRECTORY_COMPANY_REQUIRED_MESSAGE).toBe('请先选择公司');
    expect(ROOT_DIRECTORY_NAME_REQUIRED_MESSAGE).toBe('请输入顶级目录名称');
    expect(DELETE_USER_CONFIRM_MESSAGE).toBe('确定要删除该用户吗？');
  });

  it('maps known backend error codes into stable UI messages', () => {
    expect(mapUserManagementErrorMessage('managed_kb_root_node_not_found')).toContain('当前负责目录已失效');
    expect(mapUserManagementErrorMessage('managed_kb_root_node_required_for_sub_admin')).toBe(
      '请选择子管理员负责的知识库目录'
    );
    expect(mapUserManagementErrorMessage('company_required_for_sub_admin')).toBe('子管理员必须选择公司');
    expect(mapUserManagementErrorMessage('username_already_exists')).toBe('用户账号已存在');
    expect(mapUserManagementErrorMessage('unknown_error')).toBe('unknown_error');
    expect(mapUserManagementErrorMessage('')).toBe('');
  });

  it('maps reset-password validation codes', () => {
    expect(getResetPasswordValidationMessage('password_required')).toBe('请输入新密码');
    expect(getResetPasswordValidationMessage('password_mismatch')).toBe('两次输入的新密码不一致');
    expect(getResetPasswordValidationMessage('other')).toBe('');
  });
});
