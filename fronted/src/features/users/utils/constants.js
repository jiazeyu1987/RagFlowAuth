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
  username: '',
  password: '',
  email: '',
  company_id: '',
  department_id: '',
  group_ids: [],
  max_login_sessions: 3,
  idle_timeout_minutes: 120,
};

export const DEFAULT_POLICY_FORM = {
  max_login_sessions: 3,
  idle_timeout_minutes: 120,
};
