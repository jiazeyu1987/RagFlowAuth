export const USER_SEARCH_LIMIT = 20;
export const USER_SEARCH_DELAY_MS = 250;
export const VALID_TABS = new Set(['records', 'certifications']);

export const createUserSearchState = () => ({
  keyword: '',
  results: [],
  loading: false,
  open: false,
  error: '',
});

export const toDateTimeLocalValue = (value) => {
  const date = value ? new Date(Number(value)) : new Date();
  if (Number.isNaN(date.getTime())) return '';
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');
  return `${year}-${month}-${day}T${hours}:${minutes}`;
};

export const parseDateTimeLocal = (value) => {
  const text = String(value || '').trim();
  if (!text) return null;
  const timestamp = new Date(text).getTime();
  return Number.isFinite(timestamp) ? timestamp : null;
};

export const addYearsToTimestamp = (value, years) => {
  const base = new Date(Number(value));
  if (Number.isNaN(base.getTime())) return Number(value);
  base.setFullYear(base.getFullYear() + years);
  return base.getTime();
};

export const buildUserLabel = (user) => {
  if (!user) return '-';
  const fullName = String(user.full_name || '').trim();
  const username = String(user.username || '').trim();
  return fullName || username || String(user.user_id || '-');
};

export const resolvePrefillRequirementCode = (requirements, searchParams) => {
  const requestedRequirementCode = String(searchParams.get('requirement_code') || '').trim();
  if (requestedRequirementCode) {
    const matchedRequirement = (requirements || []).find(
      (item) => String(item?.requirement_code || '') === requestedRequirementCode
    );
    if (matchedRequirement) {
      return requestedRequirementCode;
    }
  }

  const requestedControlledAction = String(searchParams.get('controlled_action') || '').trim();
  if (!requestedControlledAction) {
    return '';
  }
  const matchedRequirement = (requirements || []).find(
    (item) => String(item?.controlled_action || '') === requestedControlledAction
  );
  return String(matchedRequirement?.requirement_code || '');
};
