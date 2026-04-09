const UUID_LIKE_PATTERN =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const normalizePersonName = (value) => {
  const text = String(value || '').trim();
  if (!text) return '';
  if (UUID_LIKE_PATTERN.test(text)) return '';
  return text;
};

export const buildUserDisplayLabel = (item) => {
  const fullName = normalizePersonName(item?.full_name);
  const username = String(item?.username || '').trim();
  if (fullName && username) return `${fullName}(${username})`;
  if (fullName) return fullName;
  if (username) return username;
  return String(item?.user_id || '').trim();
};

export const buildSubAdminOptions = ({ users, companyId, excludeUserId = '' }) =>
  (Array.isArray(users) ? users : [])
    .filter((item) => String(item?.role || '') === 'sub_admin')
    .filter((item) => String(item?.status || '').toLowerCase() === 'active')
    .filter((item) => String(item?.user_id || '') !== String(excludeUserId || ''))
    .filter((item) => (companyId == null ? true : Number(item?.company_id) === Number(companyId)))
    .map((item) => ({
      value: String(item?.user_id || ''),
      label: buildUserDisplayLabel(item),
      username: String(item?.username || ''),
      company_id: item?.company_id ?? null,
    }))
    .filter((item) => item.value);


export const buildUserManagementSubAdminOptions = ({
  users,
  createCompanyId,
  createEmployeeUserId,
  policyCompanyId,
  policyUserId,
}) => {
  const normalizedCreateEmployeeUserId = String(createEmployeeUserId || '').trim();
  const normalizedCreateCompanyId = createCompanyId ? Number(createCompanyId) : null;
  const normalizedPolicyCompanyId = policyCompanyId ? Number(policyCompanyId) : null;
  const normalizedPolicyUserId = String(policyUserId || '');
  const createCompanyFilter = normalizedCreateEmployeeUserId ? normalizedCreateCompanyId : null;

  return {
    subAdminOptions: buildSubAdminOptions({
      users,
      companyId: createCompanyFilter,
    }),
    policySubAdminOptions: buildSubAdminOptions({
      users,
      companyId: normalizedPolicyCompanyId,
      excludeUserId: normalizedPolicyUserId,
    }),
  };
};
