const normalizeOptionalNumber = (value) => {
  if (value == null || value === '') return null;
  const normalized = Number(value);
  return Number.isFinite(normalized) ? normalized : null;
};

export const filterDepartmentsByCompany = ({ companyId, departments }) => {
  const items = Array.isArray(departments) ? departments : [];
  const normalizedCompanyId = normalizeOptionalNumber(companyId);
  if (normalizedCompanyId == null) return items;

  return items.filter((department) => {
    const departmentCompanyId = normalizeOptionalNumber(department.company_id);
    return departmentCompanyId == null || departmentCompanyId === normalizedCompanyId;
  });
};

export const shouldClearMismatchedDepartment = ({ companyId, departmentId, departments }) => {
  const normalizedDepartmentId = normalizeOptionalNumber(departmentId);
  if (normalizedDepartmentId == null) return false;

  const selectedDepartment = (Array.isArray(departments) ? departments : []).find(
    (department) => department.id === normalizedDepartmentId
  );
  if (!selectedDepartment) return false;

  const normalizedCompanyId = normalizeOptionalNumber(companyId);
  const departmentCompanyId = normalizeOptionalNumber(selectedDepartment.company_id);
  if (normalizedCompanyId == null || departmentCompanyId == null) return false;

  return departmentCompanyId !== normalizedCompanyId;
};
