import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ManagedKbRootSection from './ManagedKbRootSection';
import ModalActionRow from './ModalActionRow';
import PermissionAssignmentHint from './PermissionAssignmentHint';
import PermissionGroupChecklist from './PermissionGroupChecklist';
import SessionLimitFields from './SessionLimitFields';
import UserModalFrame from './UserModalFrame';
import UserProfileFields from './UserProfileFields';
import { orgDirectoryApi } from '../../../orgDirectory/api';

const normalizeSearchText = (value) => String(value || '').trim();

const flattenOrgPeopleNodes = (tree) => {
  const rootNodes = Array.isArray(tree) ? tree : [];
  const stack = [...rootNodes].reverse();
  const people = [];

  while (stack.length > 0) {
    const node = stack.pop();
    if (!node || typeof node !== 'object') {
      continue;
    }

    const children = Array.isArray(node.children) ? node.children : [];
    for (let index = children.length - 1; index >= 0; index -= 1) {
      stack.push(children[index]);
    }

    if (String(node.node_type || '').toLowerCase() !== 'person') {
      continue;
    }

    people.push(node);
  }

  return people;
};

const TEXT = {
  title: '\u65b0\u5efa\u7528\u6237',
  fullName: '\u59d3\u540d',
  fullNamePlaceholder: '\u8bf7\u8f93\u5165\u59d3\u540d\u5e76\u4ece\u4e0b\u62c9\u4e2d\u9009\u62e9',
  username: '\u7528\u6237\u8d26\u53f7',
  usernamePlaceholder: '\u8bf7\u8f93\u5165\u7528\u6237\u8d26\u53f7',
  password: '\u5bc6\u7801',
  userType: '\u7528\u6237\u7c7b\u578b',
  normalUser: '\u666e\u901a\u7528\u6237',
  subAdmin: '\u5b50\u7ba1\u7406\u5458',
  company: '\u516c\u53f8',
  companyPlaceholder: '\u8bf7\u9009\u62e9\u516c\u53f8',
  department: '\u90e8\u95e8',
  departmentPlaceholder: '\u8bf7\u9009\u62e9\u90e8\u95e8',
  ownerSubAdmin: '\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458',
  ownerSubAdminPlaceholder: '\u8bf7\u9009\u62e9\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458',
  maxSessions: '\u6700\u5927\u767b\u5f55\u4f1a\u8bdd\u6570',
  idleTimeout: '\u7a7a\u95f2\u8d85\u65f6(\u5206\u949f)',
  toolPermissions: '\u5de5\u5177\u529f\u80fd',
  normalUserHint:
    '\u521b\u5efa\u666e\u901a\u7528\u6237\u65f6\u4e0d\u76f4\u63a5\u914d\u7f6e\u6743\u9650\u7ec4\uff0c\u540e\u7eed\u7531\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458\u8d1f\u8d23\u5206\u914d\u3002',
  subAdminToolHint:
    '\u521b\u5efa\u5b50\u7ba1\u7406\u5458\u65f6\uff0c\u8bf7\u76f4\u63a5\u52fe\u9009\u53ef\u5206\u914d\u7684\u5de5\u5177\u529f\u80fd\u3002',
  noTools: '\u6682\u65e0\u53ef\u5206\u914d\u7684\u5de5\u5177',
  selectedTools: '\u5df2\u9009\u62e9',
  kbRoot: '\u77e5\u8bc6\u5e93\u8d1f\u8d23\u76ee\u5f55',
  kbRootHint:
    '\u8be5\u7528\u6237\u62e5\u6709\u6240\u9009\u76ee\u5f55\u53ca\u5176\u540e\u4ee3\u7684\u5168\u90e8\u77e5\u8bc6\u5e93\u7ba1\u7406\u6743\u9650\u3002',
  employeeSearchLoading: '\u6b63\u5728\u52a0\u8f7d\u7ec4\u7ec7\u540c\u4e8b...',
  employeeSearchEmpty: '\u672a\u627e\u5230\u5339\u914d\u540c\u4e8b',
  employeeSearchError: '\u7ec4\u7ec7\u5458\u5de5\u5217\u8868\u52a0\u8f7d\u5931\u8d25',
  submit: '\u521b\u5efa',
  cancel: '\u53d6\u6d88',
};

export default function CreateUserModal({
  open,
  newUser,
  error,
  allUsers = [],
  companies,
  departments,
  subAdminOptions,
  availableTools = [],
  kbDirectoryNodes,
  kbDirectoryLoading,
  kbDirectoryError,
  kbDirectoryCreateError,
  kbDirectoryCreatingRoot,
  orgDirectoryError,
  onSubmit,
  onCancel,
  onFieldChange,
  onToggleTool,
  onCreateRootDirectory,
}) {
  const inputStyle = {
    width: '100%',
    padding: '8px',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    boxSizing: 'border-box',
  };

  const [orgPeople, setOrgPeople] = useState([]);
  const [employeeSearch, setEmployeeSearch] = useState(() => ({
    open: false,
    loading: false,
    error: '',
  }));

  const blurTimerRef = useRef(null);
  const orgPeopleRequestedRef = useRef(false);

  const isSubAdmin = String(newUser.user_type || 'normal') === 'sub_admin';

  const clearBlurTimer = useCallback(() => {
    if (blurTimerRef.current) {
      window.clearTimeout(blurTimerRef.current);
      blurTimerRef.current = null;
    }
  }, []);

  const clearSelectedEmployeeBinding = useCallback(() => {
    onFieldChange('employee_user_id', '');
    onFieldChange('company_id', '');
    onFieldChange('department_id', '');
  }, [onFieldChange]);

  const ensureOrgPeopleLoaded = useCallback(async () => {
    if (orgPeopleRequestedRef.current) {
      return;
    }
    orgPeopleRequestedRef.current = true;
    setEmployeeSearch((previous) => ({
      ...previous,
      loading: true,
      error: '',
    }));
    try {
      const tree = await orgDirectoryApi.getTree();
      setOrgPeople(flattenOrgPeopleNodes(tree));
      setEmployeeSearch((previous) => ({
        ...previous,
        loading: false,
        error: '',
      }));
    } catch (_error) {
      setOrgPeople([]);
      setEmployeeSearch((previous) => ({
        ...previous,
        loading: false,
        error: TEXT.employeeSearchError,
      }));
    }
  }, []);

  const companyNameById = useMemo(() => {
    const map = new Map();
    (Array.isArray(companies) ? companies : []).forEach((company) => {
      const key = normalizeSearchText(company?.id);
      if (!key) {
        return;
      }
      map.set(key, normalizeSearchText(company?.name));
    });
    return map;
  }, [companies]);

  const departmentNameById = useMemo(() => {
    const map = new Map();
    (Array.isArray(departments) ? departments : []).forEach((department) => {
      const key = normalizeSearchText(department?.id);
      if (!key) {
        return;
      }
      map.set(key, normalizeSearchText(department?.path_name) || normalizeSearchText(department?.name));
    });
    return map;
  }, [departments]);

  const defaultDepartmentIdByCompanyId = useMemo(() => {
    const map = new Map();
    (Array.isArray(departments) ? departments : []).forEach((department) => {
      const companyId = normalizeSearchText(department?.company_id);
      const departmentId = normalizeSearchText(department?.id ?? department?.department_id);
      if (!companyId || !departmentId || map.has(companyId)) {
        return;
      }
      map.set(companyId, departmentId);
    });
    return map;
  }, [departments]);

  const occupiedEmployeeIds = useMemo(() => {
    const set = new Set();
    (Array.isArray(allUsers) ? allUsers : []).forEach((user) => {
      const employeeUserId = normalizeSearchText(user?.employee_user_id).toLowerCase();
      if (employeeUserId) {
        set.add(employeeUserId);
      }
    });
    return set;
  }, [allUsers]);

  const selectedEmployeeUserId = normalizeSearchText(newUser.employee_user_id);
  const selectedEmployeeUserIdLower = selectedEmployeeUserId.toLowerCase();

  const employeeOptions = useMemo(() => {
    return (Array.isArray(orgPeople) ? orgPeople : [])
      .map((personNode) => {
        const employeeUserId = normalizeSearchText(personNode?.employee_user_id);
        const fullName = normalizeSearchText(personNode?.name);
        const companyId = normalizeSearchText(personNode?.company_id);
        const departmentId =
          normalizeSearchText(personNode?.department_id) || defaultDepartmentIdByCompanyId.get(companyId) || '';
        if (!employeeUserId || !fullName || !companyId || !departmentId) {
          return null;
        }

        const normalizedEmployeeUserId = employeeUserId.toLowerCase();
        if (
          normalizedEmployeeUserId !== selectedEmployeeUserIdLower
          && occupiedEmployeeIds.has(normalizedEmployeeUserId)
        ) {
          return null;
        }

        return {
          employee_user_id: employeeUserId,
          full_name: fullName,
          company_id: companyId,
          department_id: departmentId,
          company_name: companyNameById.get(companyId) || '',
          department_name: departmentNameById.get(departmentId) || '',
        };
      })
      .filter(Boolean);
  }, [
    companyNameById,
    defaultDepartmentIdByCompanyId,
    departmentNameById,
    occupiedEmployeeIds,
    orgPeople,
    selectedEmployeeUserIdLower,
  ]);

  const employeeSearchKeyword = normalizeSearchText(newUser.full_name).toLowerCase();
  const employeeSuggestions = useMemo(() => {
    const candidates = employeeSearchKeyword
      ? employeeOptions.filter((item) => {
          const fullName = normalizeSearchText(item.full_name).toLowerCase();
          const employeeUserId = normalizeSearchText(item.employee_user_id).toLowerCase();
          return fullName.includes(employeeSearchKeyword) || employeeUserId.includes(employeeSearchKeyword);
        })
      : employeeOptions;

    return candidates;
  }, [employeeOptions, employeeSearchKeyword]);

  useEffect(
    () => () => {
      clearBlurTimer();
    },
    [clearBlurTimer]
  );

  useEffect(() => {
    if (open) {
      return;
    }
    clearBlurTimer();
    orgPeopleRequestedRef.current = false;
    setOrgPeople([]);
    setEmployeeSearch({
      open: false,
      loading: false,
      error: '',
    });
  }, [clearBlurTimer, open]);

  const handleEmployeeSearchKeywordChange = useCallback(
    (nextKeyword) => {
      onFieldChange('full_name', nextKeyword);
      setEmployeeSearch((previous) => ({
        ...previous,
        open: true,
      }));
      ensureOrgPeopleLoaded();
      const selectedEmployeeId = normalizeSearchText(newUser.employee_user_id);
      if (!selectedEmployeeId) {
        return;
      }
      const selectedProfile = employeeOptions.find(
        (item) => normalizeSearchText(item.employee_user_id) === selectedEmployeeId
      );
      if (
        selectedProfile
        && normalizeSearchText(nextKeyword) === normalizeSearchText(selectedProfile.full_name)
      ) {
        return;
      }
      clearSelectedEmployeeBinding();
    },
    [clearSelectedEmployeeBinding, employeeOptions, ensureOrgPeopleLoaded, newUser.employee_user_id, onFieldChange]
  );

  const handleChangeValues = (patch) => {
    if (Object.prototype.hasOwnProperty.call(patch, 'full_name')) {
      handleEmployeeSearchKeywordChange(patch.full_name);
    }
    Object.entries(patch).forEach(([field, value]) => {
      if (field === 'full_name') {
        return;
      }
      onFieldChange(field, value);
    });
  };

  const handleEmployeeFocus = useCallback(() => {
    clearBlurTimer();
    setEmployeeSearch((previous) => ({
      ...previous,
      open: true,
    }));
    ensureOrgPeopleLoaded();
  }, [clearBlurTimer, ensureOrgPeopleLoaded]);

  const handleEmployeeBlur = useCallback(() => {
    clearBlurTimer();
    blurTimerRef.current = window.setTimeout(() => {
      setEmployeeSearch((previous) => ({
        ...previous,
        open: false,
      }));
    }, 120);
  }, [clearBlurTimer]);

  const handleSelectEmployee = useCallback(
    (item) => {
      const employeeUserId = normalizeSearchText(item?.employee_user_id);
      if (!employeeUserId) {
        return;
      }
      onFieldChange('employee_user_id', employeeUserId);
      onFieldChange('full_name', normalizeSearchText(item?.full_name));
      onFieldChange('company_id', normalizeSearchText(item?.company_id));
      onFieldChange('department_id', normalizeSearchText(item?.department_id));
      setEmployeeSearch((previous) => ({
        ...previous,
        open: false,
      }));
    },
    [onFieldChange]
  );

  const showEmployeeDropdown = employeeSearch.open && (
    employeeSearch.loading
    || Boolean(employeeSearch.error)
    || employeeSuggestions.length > 0
    || Boolean(employeeSearchKeyword)
  );

  const fullNameExtra = showEmployeeDropdown ? (
    <div
      data-testid="users-create-full-name-results"
      style={{
        position: 'absolute',
        top: 'calc(100% + 6px)',
        left: 0,
        right: 0,
        zIndex: 20,
        backgroundColor: '#ffffff',
        border: '1px solid #d1d5db',
        borderRadius: '8px',
        boxShadow: '0 10px 24px rgba(15, 23, 42, 0.12)',
        overflow: 'hidden',
      }}
    >
      {employeeSearch.loading ? (
        <div
          data-testid="users-create-full-name-loading"
          style={{ padding: '8px 10px', color: '#6b7280', fontSize: '12px' }}
        >
          {TEXT.employeeSearchLoading}
        </div>
      ) : null}

      {!employeeSearch.loading && employeeSearch.error ? (
        <div
          data-testid="users-create-full-name-error"
          style={{ padding: '8px 10px', color: '#b91c1c', fontSize: '12px' }}
        >
          {employeeSearch.error}
        </div>
      ) : null}

      {!employeeSearch.loading && !employeeSearch.error && employeeSuggestions.length === 0 ? (
        <div
          data-testid="users-create-full-name-empty"
          style={{ padding: '8px 10px', color: '#6b7280', fontSize: '12px' }}
        >
          {TEXT.employeeSearchEmpty}
        </div>
      ) : null}

      {!employeeSearch.loading && !employeeSearch.error
        ? employeeSuggestions.map((item, index) => {
            const title = item.full_name;
            const meta = [item.company_name, item.department_name].filter(Boolean).join(' / ');
            return (
              <button
                key={item.employee_user_id}
                type="button"
                data-testid={`users-create-full-name-result-${item.employee_user_id}`}
                onMouseDown={(event) => {
                  event.preventDefault();
                  handleSelectEmployee(item);
                }}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '8px 10px',
                  border: 'none',
                  borderTop: index === 0 ? 'none' : '1px solid #f3f4f6',
                  background: '#ffffff',
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontSize: '13px', color: '#111827', fontWeight: 600 }}>{title}</div>
                {meta ? (
                  <div style={{ fontSize: '12px', color: '#6b7280', marginTop: '2px' }}>{meta}</div>
                ) : null}
              </button>
            );
          })
        : null}
    </div>
  ) : null;

  return (
    <UserModalFrame open={open} title={TEXT.title} maxWidth="420px">
      {({ isMobile }) => (
        <form onSubmit={onSubmit} data-testid="users-create-form">
          <UserProfileFields
            inputStyle={inputStyle}
            values={newUser}
            onChangeValues={handleChangeValues}
            onFullNameFocus={handleEmployeeFocus}
            onFullNameBlur={handleEmployeeBlur}
            fullNameExtra={fullNameExtra}
            companies={companies}
            departments={departments}
            subAdminOptions={subAdminOptions}
            fullNamePlaceholder={TEXT.fullNamePlaceholder}
            companyDisabled
            departmentDisabled
            labels={{
              fullName: TEXT.fullName,
              company: TEXT.company,
              companyPlaceholder: TEXT.companyPlaceholder,
              department: TEXT.department,
              departmentPlaceholder: TEXT.departmentPlaceholder,
              userType: TEXT.userType,
              normalUser: TEXT.normalUser,
              subAdmin: TEXT.subAdmin,
              ownerSubAdmin: TEXT.ownerSubAdmin,
              ownerSubAdminPlaceholder: TEXT.ownerSubAdminPlaceholder,
            }}
            testIds={{
              fullName: 'users-create-full-name',
              company: 'users-create-company',
              department: 'users-create-department',
              userType: 'users-create-user-type',
              manager: 'users-create-sub-admin',
            }}
            afterFullName={
              <>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                    {TEXT.username}
                  </label>
                  <input
                    type="text"
                    required
                    autoComplete="off"
                    value={newUser.username || ''}
                    onChange={(event) => onFieldChange('username', event.target.value)}
                    placeholder={TEXT.usernamePlaceholder}
                    data-testid="users-create-username"
                    style={inputStyle}
                  />
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                    {TEXT.password}
                  </label>
                  <input
                    type="password"
                    required
                    value={newUser.password || ''}
                    onChange={(event) => onFieldChange('password', event.target.value)}
                    data-testid="users-create-password"
                    style={inputStyle}
                  />
                </div>
              </>
            }
            companyRequired
            departmentRequired
            managerRequired
            userTypeBeforeOrganization
          />

          <SessionLimitFields
            inputStyle={inputStyle}
            maxSessionsLabel={TEXT.maxSessions}
            maxSessionsValue={newUser.max_login_sessions}
            maxSessionsRequired
            maxSessionsTestId="users-create-max-login-sessions"
            onChangeMaxSessions={(event) => onFieldChange('max_login_sessions', event.target.value)}
            idleTimeoutLabel={TEXT.idleTimeout}
            idleTimeoutValue={newUser.idle_timeout_minutes}
            idleTimeoutRequired
            idleTimeoutTestId="users-create-idle-timeout"
            onChangeIdleTimeout={(event) => onFieldChange('idle_timeout_minutes', event.target.value)}
          />

          {!isSubAdmin ? (
            <PermissionAssignmentHint
              label={TEXT.toolPermissions}
              text={TEXT.normalUserHint}
              marginBottom="24px"
              panelBorderRadius="4px"
              testId="users-create-permission-hint"
            />
          ) : null}

          {isSubAdmin ? (
            <PermissionGroupChecklist
              label={TEXT.toolPermissions}
              hint={TEXT.subAdminToolHint}
              groups={availableTools}
              selectedGroupIds={newUser.tool_ids}
              onToggleGroup={onToggleTool}
              testIdPrefix="users-create-tool"
              emptyText={TEXT.noTools}
              selectedText={TEXT.selectedTools}
              loadingTestId="users-create-groups-loading"
              errorTestId="users-create-groups-error"
              marginBottom="24px"
              maxHeight={isMobile ? '220px' : '260px'}
              countSuffix="\u4e2a\u5de5\u5177"
            />
          ) : null}

          {isSubAdmin ? (
            <ManagedKbRootSection
              label={TEXT.kbRoot}
              hint={TEXT.kbRootHint}
              nodes={kbDirectoryNodes}
              selectedNodeId={newUser.managed_kb_root_node_id || ''}
              onSelect={(nodeId) => onFieldChange('managed_kb_root_node_id', nodeId)}
              loading={kbDirectoryLoading}
              error={kbDirectoryError}
              companyId={newUser.company_id}
              createRootError={kbDirectoryCreateError}
              creatingRoot={kbDirectoryCreatingRoot}
              onCreateRootDirectory={onCreateRootDirectory}
              marginBottom="24px"
            />
          ) : null}

          {orgDirectoryError ? (
            <div style={{ marginBottom: '16px', color: '#ef4444' }} data-testid="users-create-org-error">
              {orgDirectoryError}
            </div>
          ) : null}

          {error ? (
            <div style={{ marginBottom: '16px', color: '#ef4444' }} data-testid="users-create-error">
              {error}
            </div>
          ) : null}

          <ModalActionRow
            isMobile={isMobile}
            actions={[
              {
                type: 'submit',
                testId: 'users-create-submit',
                label: TEXT.submit,
                backgroundColor: '#3b82f6',
              },
              {
                onClick: onCancel,
                testId: 'users-create-cancel',
                label: TEXT.cancel,
                backgroundColor: '#6b7280',
              },
            ]}
          />
        </form>
      )}
    </UserModalFrame>
  );
}
