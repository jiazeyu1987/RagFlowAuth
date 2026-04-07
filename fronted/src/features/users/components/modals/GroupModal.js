import React from 'react';
import ModalActionRow from './ModalActionRow';
import PermissionGroupChecklist from './PermissionGroupChecklist';
import UserModalFrame from './UserModalFrame';

const TEXT = {
  title: '\u5206\u914d\u6743\u9650\u7ec4',
  label: '\u9009\u62e9\u6743\u9650\u7ec4\uff0c\u53ef\u591a\u9009',
  empty: '\u6682\u65e0\u53ef\u7528\u6743\u9650\u7ec4',
  selected: '\u5df2\u9009\u62e9',
  cancel: '\u53d6\u6d88',
  save: '\u4fdd\u5b58',
};

export default function GroupModal({
  open,
  editingGroupUser,
  availableGroups,
  permissionGroupsLoading = false,
  permissionGroupsError = null,
  selectedGroupIds,
  onToggleGroup,
  onCancel,
  onSave,
}) {
  return (
    <UserModalFrame
      open={Boolean(open && editingGroupUser)}
      testId="users-group-modal"
      title={`${TEXT.title} - ${editingGroupUser?.full_name || editingGroupUser?.username || ''}`}
      maxWidth="500px"
    >
      {({ isMobile }) => (
        <>
          <PermissionGroupChecklist
            label={TEXT.label}
            groups={availableGroups}
            loading={permissionGroupsLoading}
            error={permissionGroupsError}
            selectedGroupIds={selectedGroupIds}
            onToggleGroup={onToggleGroup}
            testIdPrefix="users-group-checkbox"
            emptyText={TEXT.empty}
            selectedText={TEXT.selected}
            loadingTestId="users-group-loading"
            errorTestId="users-group-error"
            marginBottom="24px"
            maxHeight={isMobile ? '240px' : '300px'}
            panelBorderRadius="4px"
            itemAlign="center"
            emptyPadding="8px"
          />
          <ModalActionRow
            isMobile={isMobile}
            actions={[
              {
                onClick: onCancel,
                testId: 'users-group-cancel',
                label: TEXT.cancel,
                backgroundColor: '#6b7280',
              },
              {
                onClick: onSave,
                disabled: permissionGroupsLoading || Boolean(permissionGroupsError),
                testId: 'users-group-save',
                label: TEXT.save,
                backgroundColor: '#2563eb',
              },
            ]}
          />
        </>
      )}
    </UserModalFrame>
  );
}
