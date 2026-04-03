export const DEFAULT_FILTERS = {
  q: '',
  company_id: '',
  department_id: '',
  status: '',
  group_id: '',
  created_from: '',
  created_to: '',
};

export const DEFAULT_NEW_USER = {
  full_name: '',
  username: '',
  password: '',
  user_type: 'normal',
  manager_user_id: '',
  managed_kb_root_node_id: '',
  company_id: '',
  department_id: '',
  group_ids: [],
  max_login_sessions: 3,
  idle_timeout_minutes: 120,
};

export const DEFAULT_POLICY_FORM = {
  full_name: '',
  company_id: '',
  department_id: '',
  user_type: 'normal',
  manager_user_id: '',
  managed_kb_root_node_id: '',
  group_ids: [],
  max_login_sessions: 3,
  idle_timeout_minutes: 120,
  can_change_password: true,
  disable_account: false,
  disable_mode: 'immediate',
  disable_until_date: '',
};
