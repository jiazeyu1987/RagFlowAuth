export const ORG_NO_COMPANY_MESSAGE = '组织管理中没有可用公司，无法创建或编辑用户';
export const ORG_NO_DEPARTMENT_MESSAGE = '组织管理中没有可用部门，无法创建或编辑用户';
export const ROOT_DIRECTORY_COMPANY_REQUIRED_MESSAGE = '请先选择公司';
export const ROOT_DIRECTORY_NAME_REQUIRED_MESSAGE = '请输入顶级目录名称';
export const LOAD_USERS_ERROR = '加载用户失败';
export const LOAD_ORG_DIRECTORY_ERROR = '加载组织管理数据失败';
export const LOAD_KNOWLEDGE_DIRECTORIES_ERROR = '加载知识库目录失败';
export const CREATE_USER_ERROR = '创建用户失败';
export const CREATE_ROOT_DIRECTORY_ERROR = '创建顶级目录失败';
export const DELETE_USER_CONFIRM_MESSAGE = '确定要删除该用户吗？';
export const DELETE_USER_ERROR = '删除用户失败';
export const DISABLE_USER_ERROR = '禁用用户失败';
export const TOGGLE_USER_STATUS_ERROR = '切换用户状态失败';
export const RESET_PASSWORD_REQUIRED_MESSAGE = '请输入新密码';
export const RESET_PASSWORD_MISMATCH_MESSAGE = '两次输入的新密码不一致';
export const RESET_PASSWORD_ERROR = '修改密码失败';
export const SAVE_POLICY_ERROR = '保存登录策略失败';
export const SAVE_GROUP_ERROR = '保存权限组失败';

const ERROR_MESSAGE_MAP = {
  managed_kb_root_node_not_found: '当前负责目录已失效，请先在目标公司的知识库目录中重新绑定有效目录。',
  managed_kb_root_node_required_for_sub_admin: '请选择子管理员负责的知识库目录',
  company_required_for_sub_admin: '子管理员必须选择公司',
  username_already_exists: '用户账号已存在',
};

export const mapUserManagementErrorMessage = (value) => {
  const code = String(value || '').trim();
  if (!code) return '';
  return ERROR_MESSAGE_MAP[code] || code;
};

export const getResetPasswordValidationMessage = (errorCode) => {
  if (errorCode === 'password_required') {
    return RESET_PASSWORD_REQUIRED_MESSAGE;
  }
  if (errorCode === 'password_mismatch') {
    return RESET_PASSWORD_MISMATCH_MESSAGE;
  }
  return '';
};
