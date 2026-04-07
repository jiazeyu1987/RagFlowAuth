export const shouldLoadAssignableGroups = ({ isAdminUser, isSubAdminUser }) =>
  Boolean(isAdminUser || isSubAdminUser);

export const buildUsersLoadState = (userList) => ({
  allUsers: userList,
  error: null,
});

export const buildPermissionGroupsLoadState = (availableGroups) => ({
  availableGroups,
});

export const buildPermissionGroupsLoadErrorState = () => ({
  availableGroups: [],
});

export const buildPermissionGroupsLoadErrorLogArgs = (message) => [
  'Failed to load permission groups:',
  message,
];

export const buildOrgDirectoryErrorState = (message) => ({
  companies: [],
  departments: [],
  error: message,
});

export const buildOrgDirectoryState = ({
  companyList,
  departmentList,
  noCompanyMessage,
  noDepartmentMessage,
}) => {
  const companies = Array.isArray(companyList) ? companyList : [];
  const departments = Array.isArray(departmentList) ? departmentList : [];

  if (!companies.length) {
    return {
      companies,
      departments,
      error: noCompanyMessage,
    };
  }

  if (!departments.length) {
    return {
      companies,
      departments,
      error: noDepartmentMessage,
    };
  }

  return {
    companies,
    departments,
    error: null,
  };
};
