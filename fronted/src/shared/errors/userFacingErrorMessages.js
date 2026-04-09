const EXACT_ERROR_MESSAGES = {
  admin_required: '当前操作仅管理员可执行',
  account_disabled: '当前账号已被禁用，请联系管理员',
  account_inactive: '当前账号已被禁用，请联系管理员',
  credentials_locked: '当前账号已被临时锁定，请稍后再试或联系管理员',
  invalid_source: '当前操作参数无效，请刷新后重试',
  invalid_username_or_password: '用户名或密码错误',
  missing_dataset: '缺少知识库信息，请重新选择后再试',
  missing_dataset_name: '缺少知识库信息，请重新选择后再试',
  missing_doc_id: '缺少文档标识，请刷新后重试',
  missing_file: '缺少上传文件，请重新选择后再试',
  missing_kb_id: '请先选择知识库',
  missing_session_id: '缺少任务会话，请刷新后重试',
  missing_source: '缺少操作来源，请刷新后重试',
  no_documents_selected: '请先选择文档',
  no_download_permission: '当前账号没有下载权限',
  no_knowledge_management_permission: '当前账号没有知识库管理权限',
  knowledge_management_manager_unavailable: '知识库管理服务暂不可用，请联系管理员',
  operation_approval_service_unavailable: '操作审批服务暂不可用，请联系管理员',
  operation_workflow_not_configured: '管理员尚未配置对应审批流程',
  org_structure_excel_file_required: '请先选择组织架构 Excel 文件',
  send_failed: '发送失败，请稍后重试',
  chat_not_found: '未找到指定对话',
  config_not_found: '未找到指定配置',
  source_config_not_found: '未找到源配置',
  dataset_not_found: '未找到指定知识库',
  user_not_found: '未找到指定用户',
  signature_action_required: '缺少签名动作信息，请刷新后重试',
  signature_context_user_mismatch: '当前签名令牌与登录用户不匹配，请重新发起签名',
  signature_credentials_locked: '电子签名密码已被锁定，请稍后再试或联系管理员',
  signature_meaning_required: '请填写签名用途',
  signature_not_found: '未找到电子签名记录',
  signature_password_hash_missing: '当前账号未配置电子签名密码，请联系管理员',
  signature_password_invalid: '电子签名密码错误',
  signature_password_required: '请输入电子签名密码',
  signature_reason_required: '请填写签名原因',
  signature_record_id_required: '缺少签名记录标识，请刷新后重试',
  signature_record_payload_invalid: '签名内容异常，请刷新后重试',
  signature_record_type_required: '缺少签名记录类型，请刷新后重试',
  signature_status_required: '缺少签名状态信息，请刷新后重试',
  signature_user_disabled: '当前账号已被禁用，无法使用电子签名',
  signature_user_inactive: '当前账号状态异常，无法使用电子签名',
  signature_user_not_authorized: '当前账号未开通电子签名权限，请联系管理员',
  signature_user_required: '缺少签名用户信息，请重新登录后重试',
  signature_username_required: '缺少签名用户名信息，请重新登录后重试',
  unsupported_file_type: '当前文件类型不允许上传',
  upload_extensions_loading: '正在加载允许上传的文件类型，请稍后重试',
  upload_extensions_unavailable: '暂时无法加载允许上传的文件类型，请稍后重试',
};

const PREFIX_ERROR_MESSAGES = [
  ['auth_user_invalid_', '登录返回的权限数据异常，请联系管理员'],
  ['invalid_refresh_token', '登录状态已失效，请重新登录'],
  ['operation_approval_', '操作审批处理失败，请稍后重试'],
  ['permission_groups_', '权限组数据处理失败，请联系管理员'],
  ['user_not_found:', '未找到指定用户'],
  ['notification_', '通知处理失败，请稍后重试'],
  ['search_config_', '搜索配置处理失败，请稍后重试'],
  ['knowledge_directory_', '知识库目录处理失败，请稍后重试'],
  ['ragflow_dataset_', '知识库处理失败，请稍后重试'],
  ['ragflow_document_', '文档处理失败，请稍后重试'],
  ['audit_', '审计数据处理失败，请稍后重试'],
  ['users_', '用户数据处理失败，请稍后重试'],
  ['data_security_', '数据安全处理失败，请稍后重试'],
  ['training_compliance_', '培训合规数据处理失败，请稍后重试'],
  ['chat_', '对话数据处理失败，请稍后重试'],
];

const isAsciiCode = (value) =>
  Array.from(String(value || '')).every((char) => char.charCodeAt(0) <= 0x7f);

export const mapUserFacingErrorMessage = (message, fallback = '') => {
  const code = String(message || '').trim();
  const fallbackMessage = String(fallback || '').trim();

  if (!code) {
    return fallbackMessage;
  }
  if (EXACT_ERROR_MESSAGES[code]) {
    return EXACT_ERROR_MESSAGES[code];
  }

  const prefixed = PREFIX_ERROR_MESSAGES.find(([prefix]) => code.startsWith(prefix));
  if (prefixed) {
    return prefixed[1];
  }

  if (/_invalid_payload$/.test(code)) {
    return '服务返回的数据格式异常，请联系管理员';
  }

  if (isAsciiCode(code) && /^[a-z0-9_:-]+$/i.test(code)) {
    return fallbackMessage || '操作失败，请稍后重试';
  }

  return code;
};
