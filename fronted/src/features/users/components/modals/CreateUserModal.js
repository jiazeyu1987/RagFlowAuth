import React from 'react';
import ManagedKbRootSection from './ManagedKbRootSection';
import ModalActionRow from './ModalActionRow';
import PermissionAssignmentHint from './PermissionAssignmentHint';
import PermissionGroupChecklist from './PermissionGroupChecklist';
import SessionLimitFields from './SessionLimitFields';
import UserModalFrame from './UserModalFrame';
import UserProfileFields from './UserProfileFields';

const TEXT = {
  title: '\u65b0\u5efa\u7528\u6237',
  fullName: '\u59d3\u540d',
  username: '\u7528\u6237\u8d26\u53f7',
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
  permissionGroup: '\u6743\u9650\u7ec4',
  normalUserHint:
    '\u521b\u5efa\u666e\u901a\u7528\u6237\u65f6\u4e0d\u76f4\u63a5\u914d\u7f6e\u6743\u9650\u7ec4\uff0c\u540e\u7eed\u7531\u5f52\u5c5e\u5b50\u7ba1\u7406\u5458\u8d1f\u8d23\u5206\u914d\u3002',
  subAdminPermissionHint:
    '\u53ef\u4e3a\u5b50\u7ba1\u7406\u5458\u914d\u7f6e\u53ef\u4f7f\u7528\u7684\u6743\u9650\u7ec4\uff0c\u5176\u4e2d\u7684\u5b9e\u7528\u5de5\u5177\u529f\u80fd\u4f1a\u6210\u4e3a\u5176\u5411\u4e0b\u5206\u914d\u7684\u4e0a\u9650\u3002',
  noPermissionGroups: '\u6682\u65e0\u53ef\u5206\u914d\u7684\u6743\u9650\u7ec4',
  selectedPermissionGroups: '\u5df2\u9009\u62e9',
  kbRoot: '\u77e5\u8bc6\u5e93\u8d1f\u8d23\u76ee\u5f55',
  kbRootHint:
    '\u8be5\u7528\u6237\u62e5\u6709\u6240\u9009\u76ee\u5f55\u53ca\u5176\u540e\u4ee3\u7684\u5168\u90e8\u77e5\u8bc6\u5e93\u7ba1\u7406\u6743\u9650\u3002',
  submit: '\u521b\u5efa',
  cancel: '\u53d6\u6d88',
};

export default function CreateUserModal({
  open,
  newUser,
  error,
  companies,
  departments,
  subAdminOptions,
  availableGroups,
  kbDirectoryNodes,
  kbDirectoryLoading,
  kbDirectoryError,
  kbDirectoryCreateError,
  kbDirectoryCreatingRoot,
  orgDirectoryError,
  onSubmit,
  onCancel,
  onFieldChange,
  onToggleGroup,
  onCreateRootDirectory,
}) {
  const inputStyle = {
    width: '100%',
    padding: '8px',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    boxSizing: 'border-box',
  };

  const isSubAdmin = String(newUser.user_type || 'normal') === 'sub_admin';
  const handleChangeValues = (patch) => {
    Object.entries(patch).forEach(([field, value]) => {
      onFieldChange(field, value);
    });
  };

  return (
    <UserModalFrame open={open} title={TEXT.title} maxWidth="420px">
      {({ isMobile }) => (
        <form onSubmit={onSubmit} data-testid="users-create-form">
          <UserProfileFields
            inputStyle={inputStyle}
            values={newUser}
            onChangeValues={handleChangeValues}
            afterFullName={
              <>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
                    {TEXT.username}
                  </label>
                  <input
                    type="text"
                    required
                    value={newUser.username || ''}
                    onChange={(event) => onFieldChange('username', event.target.value)}
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
            companies={companies}
            departments={departments}
            subAdminOptions={subAdminOptions}
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
              label={TEXT.permissionGroup}
              text={TEXT.normalUserHint}
              marginBottom="24px"
              panelBorderRadius="4px"
              testId="users-create-permission-hint"
            />
          ) : null}

          {isSubAdmin ? (
            <PermissionGroupChecklist
              label={TEXT.permissionGroup}
              hint={TEXT.subAdminPermissionHint}
              groups={availableGroups}
              selectedGroupIds={newUser.group_ids}
              onToggleGroup={onToggleGroup}
              testIdPrefix="users-create-group"
              emptyText={TEXT.noPermissionGroups}
              selectedText={TEXT.selectedPermissionGroups}
              marginBottom="24px"
              maxHeight={isMobile ? '220px' : '260px'}
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
