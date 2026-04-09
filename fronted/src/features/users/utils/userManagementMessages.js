export const ORG_NO_COMPANY_MESSAGE = '\u7ec4\u7ec7\u7ba1\u7406\u4e2d\u6ca1\u6709\u53ef\u7528\u516c\u53f8\uff0c\u65e0\u6cd5\u521b\u5efa\u6216\u7f16\u8f91\u7528\u6237';
export const ORG_NO_DEPARTMENT_MESSAGE = '\u7ec4\u7ec7\u7ba1\u7406\u4e2d\u6ca1\u6709\u53ef\u7528\u90e8\u95e8\uff0c\u65e0\u6cd5\u521b\u5efa\u6216\u7f16\u8f91\u7528\u6237';
export const ROOT_DIRECTORY_COMPANY_REQUIRED_MESSAGE = '\u8bf7\u5148\u9009\u62e9\u516c\u53f8';
export const ROOT_DIRECTORY_NAME_REQUIRED_MESSAGE = '\u8bf7\u8f93\u5165\u9876\u7ea7\u76ee\u5f55\u540d\u79f0';
export const LOAD_USERS_ERROR = '\u52a0\u8f7d\u7528\u6237\u5931\u8d25';
export const LOAD_ORG_DIRECTORY_ERROR = '\u52a0\u8f7d\u7ec4\u7ec7\u7ba1\u7406\u6570\u636e\u5931\u8d25';
export const LOAD_KNOWLEDGE_DIRECTORIES_ERROR = '\u52a0\u8f7d\u77e5\u8bc6\u5e93\u76ee\u5f55\u5931\u8d25';
export const CREATE_USER_ERROR = '\u521b\u5efa\u7528\u6237\u5931\u8d25';
export const CREATE_ROOT_DIRECTORY_ERROR = '\u521b\u5efa\u9876\u7ea7\u76ee\u5f55\u5931\u8d25';
export const DELETE_USER_CONFIRM_MESSAGE = '\u786e\u5b9a\u8981\u5220\u9664\u8be5\u7528\u6237\u5417\uff1f';
export const DELETE_USER_ERROR = '\u5220\u9664\u7528\u6237\u5931\u8d25';
export const DISABLE_USER_ERROR = '\u7981\u7528\u7528\u6237\u5931\u8d25';
export const TOGGLE_USER_STATUS_ERROR = '\u5207\u6362\u7528\u6237\u72b6\u6001\u5931\u8d25';
export const RESET_PASSWORD_REQUIRED_MESSAGE = '\u8bf7\u8f93\u5165\u65b0\u5bc6\u7801';
export const RESET_PASSWORD_MISMATCH_MESSAGE = '\u4e24\u6b21\u8f93\u5165\u7684\u65b0\u5bc6\u7801\u4e0d\u4e00\u81f4';
export const RESET_PASSWORD_ERROR = '\u4fee\u6539\u5bc6\u7801\u5931\u8d25';
export const SAVE_POLICY_ERROR = '\u4fdd\u5b58\u767b\u5f55\u7b56\u7565\u5931\u8d25';
export const SAVE_GROUP_ERROR = '\u4fdd\u5b58\u6743\u9650\u7ec4\u5931\u8d25';
export const SAVE_TOOL_ERROR = '\u4fdd\u5b58\u5de5\u5177\u6743\u9650\u5931\u8d25';

const ERROR_MESSAGE_MAP = {
  managed_kb_root_node_not_found:
    '\u5f53\u524d\u8d1f\u8d23\u76ee\u5f55\u5df2\u5931\u6548\uff0c\u8bf7\u5148\u5728\u76ee\u6807\u516c\u53f8\u7684\u77e5\u8bc6\u5e93\u76ee\u5f55\u4e2d\u91cd\u65b0\u7ed1\u5b9a\u6709\u6548\u76ee\u5f55\u3002',
  managed_kb_root_node_required_for_sub_admin:
    '\u8bf7\u9009\u62e9\u5b50\u7ba1\u7406\u5458\u8d1f\u8d23\u7684\u77e5\u8bc6\u5e93\u76ee\u5f55',
  company_required_for_sub_admin: '\u5b50\u7ba1\u7406\u5458\u5fc5\u987b\u9009\u62e9\u516c\u53f8',
  username_already_exists: '\u7528\u6237\u8d26\u53f7\u5df2\u5b58\u5728',
  employee_user_id_required: '\u8bf7\u4ece\u59d3\u540d\u4e0b\u62c9\u4e2d\u9009\u62e9\u7ec4\u7ec7\u540c\u4e8b',
  employee_user_id_not_found: '\u9009\u62e9\u7684\u5458\u5de5UserID\u4e0d\u5b58\u5728\u4e8e\u5f53\u524d\u7ec4\u7ec7',
  employee_user_id_already_bound: '\u8be5\u7ec4\u7ec7\u5458\u5de5\u5df2\u7ed1\u5b9a\u5176\u4ed6\u7528\u6237\u8d26\u53f7',
  employee_org_profile_mismatch: '\u63d0\u4ea4\u7684\u59d3\u540d\u6216\u7ec4\u7ec7\u5f52\u5c5e\u4e0e\u5458\u5de5\u6863\u6848\u4e0d\u4e00\u81f4',
  default_department_not_found_for_company:
    '\u8be5\u5458\u5de5\u5728\u7ec4\u7ec7\u4e2d\u672a\u914d\u7f6e\u90e8\u95e8\uff0c\u4e14\u6240\u5728\u516c\u53f8\u6ca1\u6709\u53ef\u7528\u9ed8\u8ba4\u90e8\u95e8',
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
