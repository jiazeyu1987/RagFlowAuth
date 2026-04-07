import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { permissionGroupsApi } from '../../permissionGroups/api';
import { usersApi } from '../api';
import { orgDirectoryApi } from '../../orgDirectory/api';
import { DEFAULT_FILTERS } from '../utils/constants';
import { buildListParams } from '../utils/userFilters';
import {
  buildOrgDirectoryDisabledState,
  buildOrgDirectoryErrorState,
  buildOrgDirectoryState,
  buildPermissionGroupsLoadErrorLogArgs,
  buildPermissionGroupsLoadState,
  buildPermissionGroupsLoadErrorState,
  buildUsersLoadState,
  shouldLoadAssignableGroups,
  shouldLoadOrgDirectory,
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
  const [permissionGroupsLoading, setPermissionGroupsLoading] = useState(false);
  const [permissionGroupsError, setPermissionGroupsError] = useState(null);
  const [companies, setCompanies] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [orgDirectoryError, setOrgDirectoryError] = useState(null);
  const availableGroupsRef = useRef([]);
  const permissionGroupsLoadedRef = useRef(false);
  const permissionGroupsRequestRef = useRef(null);

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
    const nextAvailableGroups = Array.isArray(nextState.availableGroups)
      ? nextState.availableGroups
      : [];
    availableGroupsRef.current = nextAvailableGroups;
    setAvailableGroups(nextAvailableGroups);
    setPermissionGroupsError(nextState.error ?? null);
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
      permissionGroupsLoadedRef.current = true;
      runStateAction(
        applyPermissionGroupsState,
        buildPermissionGroupsLoadErrorState
      );
      return {
        ok: false,
        skipped: true,
        result: [],
      };
    }

    if (permissionGroupsLoadedRef.current) {
      return {
        ok: true,
        cached: true,
        result: availableGroupsRef.current,
      };
    }

    if (permissionGroupsRequestRef.current) {
      return permissionGroupsRequestRef.current;
    }

    const request = runUserManagementMutation({
      execute: () => permissionGroupsApi.listAssignable(),
      mapErrorMessage: (message) => message,
      fallbackMessage: 'permission_groups_load_failed',
      onMappedError: (message) => {
        permissionGroupsLoadedRef.current = false;
        console.error(...buildPermissionGroupsLoadErrorLogArgs(message));
        runStateAction(
          applyPermissionGroupsState,
          buildPermissionGroupsLoadErrorState,
          message
        );
      },
      onSuccess: (data) => {
        permissionGroupsLoadedRef.current = true;
        runStateAction(applyPermissionGroupsState, buildPermissionGroupsLoadState, data);
      },
      onFinally: () => {
        permissionGroupsRequestRef.current = null;
      },
      setPending: setPermissionGroupsLoading,
    });
    permissionGroupsRequestRef.current = request;
    return request;
  }, [applyPermissionGroupsState, isAdminUser, isSubAdminUser]);

  const fetchOrgDirectory = useCallback(async () => {
    if (!shouldLoadOrgDirectory({ isAdminUser })) {
      runStateAction(
        applyOrgDirectoryState,
        buildOrgDirectoryDisabledState
      );
      return;
    }

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
  }, [applyOrgDirectoryState, isAdminUser]);

  useEffect(() => {
    fetchUsers();
    fetchOrgDirectory();
  }, [fetchOrgDirectory, fetchUsers]);

  return {
    allUsers,
    loading,
    error,
    canManageUsers,
    availableGroups,
    permissionGroupsLoading,
    permissionGroupsError,
    companies,
    departments,
    orgDirectoryError,
    fetchUsers,
    fetchPermissionGroups,
    setError,
  };
};
