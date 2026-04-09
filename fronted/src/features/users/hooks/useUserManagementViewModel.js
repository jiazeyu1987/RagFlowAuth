import { useCallback, useMemo, useState } from 'react';
import { DEFAULT_FILTERS } from '../utils/constants';
import { filterUsers, groupUsersByDepartment } from '../utils/userFilters';
import { buildUserManagementSubAdminOptions } from '../utils/userSubAdminOptions';

export const useUserManagementViewModel = ({
  allUsers,
  createCompanyId,
  createEmployeeUserId,
  policyCompanyId,
  policyUserId,
}) => {
  const [filters, setFilters] = useState(DEFAULT_FILTERS);

  const filteredUsers = useMemo(() => filterUsers(allUsers, filters), [allUsers, filters]);
  const groupedUsers = useMemo(() => groupUsersByDepartment(filteredUsers), [filteredUsers]);

  const { subAdminOptions, policySubAdminOptions } = useMemo(
    () =>
      buildUserManagementSubAdminOptions({
        users: allUsers,
        createCompanyId,
        createEmployeeUserId,
        policyCompanyId,
        policyUserId,
      }),
    [allUsers, createCompanyId, createEmployeeUserId, policyCompanyId, policyUserId]
  );

  const handleResetFilters = useCallback(() => {
    setFilters(DEFAULT_FILTERS);
  }, []);

  return {
    filters,
    setFilters,
    filteredUsers,
    groupedUsers,
    subAdminOptions,
    policySubAdminOptions,
    handleResetFilters,
  };
};
