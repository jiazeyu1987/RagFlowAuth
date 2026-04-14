const EXACT_ERROR_MESSAGES = {
  admin_required: 'This action can only be performed by an administrator.',
  account_disabled: 'This account has been disabled. Please contact an administrator.',
  account_inactive: 'This account is inactive. Please contact an administrator.',
  credentials_locked: 'This account is temporarily locked. Please try again later or contact an administrator.',
  invalid_source: 'The operation parameter is invalid. Please refresh and try again.',
  invalid_username_or_password: 'Invalid username or password.',
  missing_dataset: 'Dataset information is missing. Please select a dataset again and retry.',
  missing_dataset_name: 'Dataset information is missing. Please select a dataset again and retry.',
  missing_doc_id: 'Document identifier is missing. Please refresh and try again.',
  missing_file: 'No file was provided. Please select a file and try again.',
  missing_kb_id: 'Please select a knowledge base first.',
  missing_session_id: 'Task session information is missing. Please refresh and try again.',
  missing_source: 'Operation source is missing. Please refresh and try again.',
  no_documents_selected: 'Please select at least one document first.',
  no_download_permission: 'The current account does not have download permission.',
  no_knowledge_management_permission: '当前账号没有知识库管理权限',
  knowledge_management_manager_unavailable: 'Knowledge base management service is unavailable. Please contact an administrator.',
  document_control_approval_role_conflict: 'The approver must be different from the reviewer.',
  document_control_reviewer_required: 'A reviewer must complete the review step before approval.',
  product_name_required: 'Please provide the product name.',
  registration_ref_required: 'Please provide the registration reference.',
  training_assignment_read_time_not_reached: 'The minimum reading duration has not been reached yet.',
  operation_approval_service_unavailable: 'Operation approval service is unavailable. Please contact an administrator.',
  operation_workflow_not_configured: 'The required approval workflow is not configured. Please contact an administrator.',
  org_structure_excel_file_required: 'Please select an organizational structure Excel file first.',
  send_failed: 'Send failed. Please try again later.',
  chat_not_found: 'The specified chat was not found.',
  config_not_found: 'The specified configuration was not found.',
  source_config_not_found: 'The source configuration was not found.',
  dataset_not_found: 'The specified knowledge base was not found.',
  user_not_found: 'The specified user was not found.',
  signature_action_required: 'Signature action information is missing. Please refresh and try again.',
  signature_context_user_mismatch: 'The signature token does not match the logged-in user. Please initiate signing again.',
  signature_credentials_locked: 'The electronic signature password is locked. Please try again later or contact an administrator.',
  signature_meaning_required: 'Please provide the signature purpose.',
  signature_not_found: 'The electronic signature record was not found.',
  signature_password_hash_missing: 'No electronic signature password is configured for this account. Please contact an administrator.',
  signature_password_invalid: 'The electronic signature password is incorrect.',
  signature_password_required: 'Please enter the electronic signature password.',
  signature_reason_required: 'Please provide the signature reason.',
  signature_record_id_required: 'Signature record identifier is missing. Please refresh and try again.',
  signature_record_payload_invalid: 'Signature content is invalid. Please refresh and try again.',
  signature_record_type_required: 'Signature record type is missing. Please refresh and try again.',
  signature_status_required: 'Signature status information is missing. Please refresh and try again.',
  signature_user_disabled: 'This account is disabled and cannot use electronic signatures.',
  signature_user_inactive: 'This account status is invalid and cannot use electronic signatures.',
  signature_user_not_authorized: 'This account is not authorized for electronic signatures. Please contact an administrator.',
  signature_user_required: 'Signature user information is missing. Please sign in again and retry.',
  signature_username_required: 'Signature username information is missing. Please sign in again and retry.',
  step_photo_captured_at_invalid: 'The photo capture time is invalid. Please upload the photo again.',
  step_photo_data_url_invalid: 'The photo data is invalid. Please upload the photo again.',
  step_photo_evidence_invalid: 'The photo evidence format is invalid. Please upload the photo again.',
  step_photo_evidences_invalid: 'The photo evidence list is invalid. Please upload the photo again.',
  step_photo_evidences_too_many: 'Too many photos were attached. Please keep at most 5 photos per step.',
  step_photo_empty: 'The uploaded photo is empty. Please upload a valid image.',
  step_photo_filename_required: 'The photo filename is missing. Please upload the photo again.',
  step_photo_media_type_invalid: 'Only image files can be attached as on-site photo evidence.',
  step_photo_media_type_required: 'The photo type is missing. Please upload the photo again.',
  step_photo_read_failed: 'The photo could not be read. Please upload it again.',
  step_photo_too_large: 'The photo is too large. Please keep each image under 2.5 MB.',
  unsupported_file_type: 'This file type is not supported for upload.',
  upload_extensions_loading: 'Allowed upload file types are still loading. Please try again shortly.',
  upload_extensions_unavailable: 'Allowed upload file types are temporarily unavailable. Please try again later.',
};

const PREFIX_ERROR_MESSAGES = [
  ['auth_user_invalid_', 'Permission data returned during sign-in is invalid. Please contact an administrator.'],
  ['invalid_refresh_token', 'Your sign-in session is no longer valid. Please sign in again.'],
  ['operation_approval_', 'Operation approval processing failed. Please try again later.'],
  ['permission_groups_', 'Permission group data processing failed. Please contact an administrator.'],
  ['user_not_found:', 'The specified user was not found.'],
  ['notification_', 'Notification processing failed. Please try again later.'],
  ['search_config_', 'Search configuration processing failed. Please try again later.'],
  ['knowledge_directory_', 'Knowledge directory processing failed. Please try again later.'],
  ['ragflow_dataset_', 'Knowledge base processing failed. Please try again later.'],
  ['ragflow_document_', 'Document processing failed. Please try again later.'],
  ['audit_', 'Audit data processing failed. Please try again later.'],
  ['users_', 'User data processing failed. Please try again later.'],
  ['data_security_', 'Data security processing failed. Please try again later.'],
  ['training_compliance_', 'Training compliance data processing failed. Please try again later.'],
  ['chat_', 'Chat data processing failed. Please try again later.'],
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
    return 'The response payload format is invalid. Please contact an administrator.';
  }

  if (isAsciiCode(code) && /^[a-z0-9_:-]+$/i.test(code)) {
    return fallbackMessage || 'The operation failed. Please try again later.';
  }

  return code;
};
