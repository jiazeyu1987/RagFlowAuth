import React from 'react';
import DisableAccountSection from './DisableAccountSection';
import ManagedKbRootSection from './ManagedKbRootSection';
import ModalActionRow from './ModalActionRow';
import PermissionAssignmentHint from './PermissionAssignmentHint';
import PermissionGroupChecklist from './PermissionGroupChecklist';
import SessionLimitFields from './SessionLimitFields';
import UserModalFrame from './UserModalFrame';
import UserProfileFields from './UserProfileFields';

const TEXT = {
  titlePrefix: '\u7528\u6237\u914d\u7f6e',
  baseInfo: '\u57fa\u7840\u4fe1\u606f',
  fullName: '\u59d3\u540d',
  company: '\u516c\u53f8',
  companyPlaceholder: '\u8bf7\u9009\u62e9\u516c\u53f8',
  department: '\u90e8\u95e8',
  departmentPlaceholder: '\u8bf7\u9009\u62e9\u90e8\u95e8',
  userType: '\u7528\u6237\u7c7b\u578b',
  admin: '\u7ba1\u7406\u5458',
  normalUser: '\u666e\u901a\u7528\u6237',
  subAdmin: '\u5b50\u7ba1\u7406\u5458',
  ownerSubAdmin: '\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458',
  ownerSubAdminPlaceholder: '\u8bf7\u9009\u62e9\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458',
  kbRoot: '\u77e5\u8bc6\u5e93\u8d1f\u8d23\u76ee\u5f55',
  kbRootHint:
    '\u8be5\u7528\u6237\u62e5\u6709\u6240\u9009\u76ee\u5f55\u53ca\u5176\u540e\u4ee3\u7684\u5168\u90e8\u77e5\u8bc6\u5e93\u7ba1\u7406\u6743\u9650\u3002',
  kbRootInvalid:
    '\u5f53\u524d\u8d1f\u8d23\u76ee\u5f55\u5df2\u5931\u6548\uff0c\u9700\u91cd\u65b0\u5728\u8be5\u516c\u53f8\u7684\u77e5\u8bc6\u5e93\u76ee\u5f55\u6811\u4e2d\u7ed1\u5b9a\u4e00\u4e2a\u6709\u6548\u76ee\u5f55\u3002',
  permissionGroup: '\u6743\u9650\u7ec4',
  permissionHint:
    '\u666e\u901a\u7528\u6237\u7684\u6743\u9650\u7ec4\u7531\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458\u5206\u914d\uff0c\u7ba1\u7406\u5458\u5728\u6b64\u4e0d\u76f4\u63a5\u914d\u7f6e\u3002',
  subAdminPermissionHint:
    '\u53ef\u4e3a\u5b50\u7ba1\u7406\u5458\u914d\u7f6e\u53ef\u4f7f\u7528\u7684\u6743\u9650\u7ec4\uff0c\u5176\u4e2d\u7684\u5b9e\u7528\u5de5\u5177\u529f\u80fd\u4f1a\u6210\u4e3a\u5176\u5411\u4e0b\u5206\u914d\u7684\u4e0a\u9650\u3002',
  noPermissionGroups: '\u6682\u65e0\u53ef\u5206\u914d\u7684\u6743\u9650\u7ec4',
  selectedPermissionGroups: '\u5df2\u9009\u62e9',
  loginPolicy: '\u767b\u5f55\u7b56\u7565',
  maxSessions: '\u6700\u5927\u767b\u5f55\u4f1a\u8bdd\u6570 (1-1000)',
  idleTimeout: '\u7a7a\u95f2\u8d85\u65f6 (\u5206\u949f, 1-43200)',
  disablePasswordChange: '\u4e0d\u5141\u8bb8\u6b64\u7528\u6237\u4fee\u6539\u5bc6\u7801',
  cancel: '\u53d6\u6d88',
  save: '\u4fdd\u5b58',
  saving: '\u63d0\u4ea4\u4e2d...',
};

export default function PolicyModal({
  open,
  user,
  policyForm,
  companies,
  departments,
  policySubAdminOptions,
  availableGroups,
  permissionGroupsLoading = false,
  permissionGroupsError = null,
  kbDirectoryNodes,
  kbDirectoryLoading,
  kbDirectoryError,
  kbDirectoryCreateError,
  kbDirectoryCreatingRoot,
  managedKbRootInvalid,
  orgDirectoryError,
  policyError,
  policySubmitting,
  onChangePolicyForm,
  onToggleGroup,
  onCancel,
  onSave,
  onCreateRootDirectory,
}) {
  const inputStyle = {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    boxSizing: 'border-box',
    backgroundColor: 'white',
  };

  const isBuiltInAdmin = String(user?.role || '') === 'admin';
  const isSubAdmin = String(policyForm.user_type || 'normal') === 'sub_admin';
  const applyPolicyChanges = (patch) => onChangePolicyForm({ ...policyForm, ...patch });

  return (
    <UserModalFrame
      open={Boolean(open && user)}
      testId="users-policy-modal"
      title={`${TEXT.titlePrefix} - ${user?.full_name || user?.username || ''}`}
      maxWidth="680px"
    >
      {({ isMobile }) => (
        <>
          <div style={{ marginBottom: 24 }}>
            <div style={{ fontWeight: 700, marginBottom: 12, color: '#111827' }}>{TEXT.baseInfo}</div>

            <UserProfileFields
              inputStyle={inputStyle}
              values={policyForm}
              onChangeValues={applyPolicyChanges}
              companies={companies}
              departments={departments}
              subAdminOptions={policySubAdminOptions}
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
                fullName: 'users-policy-full-name',
                company: 'users-policy-company',
                department: 'users-policy-department',
                userType: 'users-policy-user-type',
                userTypeReadonly: 'users-policy-role-admin-readonly',
                manager: 'users-policy-sub-admin',
              }}
              showManager={!isBuiltInAdmin}
              readonlyUserType={isBuiltInAdmin}
              userTypeReadonlyLabel={TEXT.admin}
              resetDepartmentOnCompanyChange
            />

            {isSubAdmin ? (
              <ManagedKbRootSection
                label={TEXT.kbRoot}
                hint={TEXT.kbRootHint}
                nodes={kbDirectoryNodes}
                selectedNodeId={policyForm.managed_kb_root_node_id || ''}
                onSelect={(nodeId) => onChangePolicyForm({ ...policyForm, managed_kb_root_node_id: nodeId })}
                loading={kbDirectoryLoading}
                error={kbDirectoryError}
                companyId={policyForm.company_id}
                createRootError={kbDirectoryCreateError}
                creatingRoot={kbDirectoryCreatingRoot}
                onCreateRootDirectory={onCreateRootDirectory}
                invalidText={TEXT.kbRootInvalid}
                invalidTestId="users-policy-invalid-kb-root"
                showInvalidWarning={managedKbRootInvalid}
                marginBottom={16}
              />
            ) : null}

            {isSubAdmin && !isBuiltInAdmin ? (
              <PermissionGroupChecklist
                label={TEXT.permissionGroup}
                hint={TEXT.subAdminPermissionHint}
                groups={availableGroups}
                loading={permissionGroupsLoading}
                error={permissionGroupsError}
                selectedGroupIds={policyForm.group_ids}
                onToggleGroup={onToggleGroup}
                testIdPrefix="users-policy-group"
                emptyText={TEXT.noPermissionGroups}
                selectedText={TEXT.selectedPermissionGroups}
                loadingTestId="users-policy-groups-loading"
                errorTestId="users-policy-groups-error"
                marginBottom={16}
                maxHeight={isMobile ? '220px' : '260px'}
              />
            ) : null}

            {!isSubAdmin && !isBuiltInAdmin ? (
              <PermissionAssignmentHint
                label={TEXT.permissionGroup}
                text={TEXT.permissionHint}
                marginBottom={8}
                fontSize={undefined}
                testId="users-policy-permission-hint"
              />
            ) : null}
          </div>

          <div style={{ marginBottom: 24 }}>
            <div style={{ fontWeight: 700, marginBottom: 12, color: '#111827' }}>{TEXT.loginPolicy}</div>

            <SessionLimitFields
              inputStyle={inputStyle}
              maxSessionsLabel={TEXT.maxSessions}
              maxSessionsValue={policyForm.max_login_sessions}
              maxSessionsTestId="users-policy-max-login-sessions"
              onChangeMaxSessions={(event) =>
                onChangePolicyForm({ ...policyForm, max_login_sessions: event.target.value })
              }
              idleTimeoutLabel={TEXT.idleTimeout}
              idleTimeoutValue={policyForm.idle_timeout_minutes}
              idleTimeoutTestId="users-policy-idle-timeout"
              onChangeIdleTimeout={(event) =>
                onChangePolicyForm({ ...policyForm, idle_timeout_minutes: event.target.value })
              }
            />

            <div style={{ marginBottom: 12 }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  data-testid="users-policy-can-change-password"
                  checked={policyForm.can_change_password === false}
                  onChange={(event) =>
                    onChangePolicyForm({ ...policyForm, can_change_password: !event.target.checked })
                  }
                />
                {TEXT.disablePasswordChange}
              </label>
            </div>

            <DisableAccountSection
              enabled={!!policyForm.disable_account}
              mode={policyForm.disable_mode}
              untilDate={policyForm.disable_until_date}
              onChangeMode={(disable_mode) => onChangePolicyForm({ ...policyForm, disable_mode })}
              onChangeUntilDate={(disable_until_date) =>
                onChangePolicyForm({ ...policyForm, disable_until_date })
              }
              showEnabledToggle
              onToggleEnabled={(disable_account) => onChangePolicyForm({ ...policyForm, disable_account })}
              radioName="users-policy-disable-mode"
              enabledTestId="users-policy-disable-account-enabled"
              immediateTestId="users-policy-disable-mode-immediate"
              untilTestId="users-policy-disable-mode-until"
              dateTestId="users-policy-disable-until-date"
              inputStyle={inputStyle}
            />
          </div>

          {orgDirectoryError ? (
            <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-policy-org-error">
              {orgDirectoryError}
            </div>
          ) : null}

          {policyError ? (
            <div style={{ marginBottom: 16, color: '#ef4444' }} data-testid="users-policy-error">
              {policyError}
            </div>
          ) : null}

          <ModalActionRow
            isMobile={isMobile}
            actions={[
              {
                onClick: onCancel,
                disabled: policySubmitting,
                testId: 'users-policy-cancel',
                label: TEXT.cancel,
                backgroundColor: '#6b7280',
              },
              {
                onClick: onSave,
                disabled: policySubmitting,
                testId: 'users-policy-save',
                label: policySubmitting ? TEXT.saving : TEXT.save,
                backgroundColor: '#0ea5e9',
                disabledBackgroundColor: '#7dd3fc',
              },
            ]}
          />
        </>
      )}
    </UserModalFrame>
  );
}
