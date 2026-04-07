import { useCallback, useEffect, useMemo, useState } from 'react';
import { permissionGroupsApi } from '../../permissionGroups/api';
import { usersApi } from '../api';
import { orgDirectoryApi } from '../../orgDirectory/api';
import { DEFAULT_FILTERS } from '../utils/constants';
import { buildListParams } from '../utils/userFilters';
import {
  buildOrgDirectoryErrorState,
  buildOrgDirectoryState,
  buildPermissionGroupsLoadErrorLogArgs,
  buildPermissionGroupsLoadState,
  buildPermissionGroupsLoadErrorState,
  buildUsersLoadState,
  shouldLoadAssignableGroups,
} from '../utils/userManagementDataResources';
import {
  LOAD_ORG_DIRECTORY_ERROR,
  LOAD_USERS_ERROR,
  ORG_NO_COMPANY_MESSAGE,
  ORG_NO_DEPARTMENT_MESSAGE,
  mapUserManagementErrorMessage,
} from '../utils/userManagementMessages';
import { runStateAction } from '../utils/userManagementActionRunners';
import { runUserManagementMutation } from '../utils/userManagementMutations';

export const useUserManagementData = ({ can, isAdminUser, isSubAdminUser }) => {
  const [allUsers, setAllUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [availableGroups, setAvailableGroups] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [orgDirectoryError, setOrgDirectoryError] = useState(null);

  const canManageUsers = useMemo(() => can('users', 'manage'), [can]);

  const applyUsersLoadState = useCallback((nextState) => {
    setAllUsers(nextState.allUsers);
    setError(nextState.error);
  }, []);

  const applyOrgDirectoryState = useCallback((nextState) => {
    setCompanies(nextState.companies);
    setDepartments(nextState.departments);
    setOrgDirectoryError(nextState.error);
  }, []);

  const applyPermissionGroupsState = useCallback((nextState) => {
    setAvailableGroups(nextState.availableGroups);
  }, []);

  const fetchUsers = useCallback(async () => {
    await runUserManagementMutation({
      execute: () => usersApi.list(buildListParams(DEFAULT_FILTERS)),
      mapErrorMessage: mapUserManagementErrorMessage,
      fallbackMessage: LOAD_USERS_ERROR,
      onMappedError: setError,
      onSuccess: (data) => runStateAction(applyUsersLoadState, buildUsersLoadState, data),
      setPending: setLoading,
    });
  }, [applyUsersLoadState]);

  const fetchPermissionGroups = useCallback(async () => {
    if (!shouldLoadAssignableGroups({ isAdminUser, isSubAdminUser })) {
      runStateAction(
        applyPermissionGroupsState,
        buildPermissionGroupsLoadErrorState
      );
      return;
    }

    await runUserManagementMutation({
      execute: () => permissionGroupsApi.listAssignable(),
      mapErrorMessage: (message) => message,
      fallbackMessage: 'permission_groups_load_failed',
      onMappedError: (message) => {
        console.error(...buildPermissionGroupsLoadErrorLogArgs(message));
        runStateAction(
          applyPermissionGroupsState,
          buildPermissionGroupsLoadErrorState
        );
      },
      onSuccess: (data) =>
        runStateAction(applyPermissionGroupsState, buildPermissionGroupsLoadState, data),
    });
  }, [applyPermissionGroupsState, isAdminUser, isSubAdminUser]);

  const fetchOrgDirectory = useCallback(async () => {
    await runUserManagementMutation({
      execute: () =>
        Promise.all([
          orgDirectoryApi.listCompanies(),
          orgDirectoryApi.listDepartments(),
        ]),
      mapErrorMessage: mapUserManagementErrorMessage,
      fallbackMessage: LOAD_ORG_DIRECTORY_ERROR,
      onMappedError: (message) =>
        runStateAction(applyOrgDirectoryState, buildOrgDirectoryErrorState, message),
      onSuccess: ([companyList, departmentList]) => {
        runStateAction(
          applyOrgDirectoryState,
          buildOrgDirectoryState,
          {
            companyList,
            departmentList,
            noCompanyMessage: ORG_NO_COMPANY_MESSAGE,
            noDepartmentMessage: ORG_NO_DEPARTMENT_MESSAGE,
          }
        );
      },
    });
  }, [applyOrgDirectoryState]);

  useEffect(() => {
    fetchUsers();
    fetchPermissionGroups();
    fetchOrgDirectory();
  }, [fetchOrgDirectory, fetchPermissionGroups, fetchUsers]);

  return {
    allUsers,
    loading,
    error,
    canManageUsers,
    availableGroups,
    companies,
    departments,
    orgDirectoryError,
    fetchUsers,
    setError,
  };
};
