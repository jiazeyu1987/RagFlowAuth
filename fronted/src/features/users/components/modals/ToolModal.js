import React from 'react';
import ModalActionRow from './ModalActionRow';
import PermissionGroupChecklist from './PermissionGroupChecklist';
import UserModalFrame from './UserModalFrame';

const TEXT = {
  title: '\u5206\u914d\u5de5\u5177\u529f\u80fd',
  label: '\u9009\u62e9\u5de5\u5177\u529f\u80fd\uff0c\u53ef\u591a\u9009',
  empty: '\u6682\u65e0\u53ef\u5206\u914d\u7684\u5de5\u5177',
  selected: '\u5df2\u9009\u62e9',
  cancel: '\u53d6\u6d88',
  save: '\u4fdd\u5b58',
};

export default function ToolModal({
  open,
  editingToolUser,
  availableTools,
  selectedToolIds,
  onToggleTool,
  onCancel,
  onSave,
}) {
  return (
    <UserModalFrame
      open={Boolean(open && editingToolUser)}
      testId="users-tool-modal"
      title={`${TEXT.title} - ${editingToolUser?.full_name || editingToolUser?.username || ''}`}
      maxWidth="500px"
    >
      {({ isMobile }) => (
        <>
          <PermissionGroupChecklist
            label={TEXT.label}
            groups={availableTools}
            selectedGroupIds={selectedToolIds}
            onToggleGroup={onToggleTool}
            testIdPrefix="users-tool-checkbox"
            emptyText={TEXT.empty}
            selectedText={TEXT.selected}
            marginBottom="24px"
            maxHeight={isMobile ? '240px' : '300px'}
            panelBorderRadius="4px"
            itemAlign="center"
            emptyPadding="8px"
            countSuffix="\u4e2a\u5de5\u5177"
          />
          <ModalActionRow
            isMobile={isMobile}
            actions={[
              {
                onClick: onCancel,
                testId: 'users-tool-cancel',
                label: TEXT.cancel,
                backgroundColor: '#6b7280',
              },
              {
                onClick: onSave,
                testId: 'users-tool-save',
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
