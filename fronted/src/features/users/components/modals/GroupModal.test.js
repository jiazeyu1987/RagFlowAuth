import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import GroupModal from './GroupModal';

jest.mock('../../../../shared/hooks/useMobileBreakpoint', () => jest.fn(() => false));

describe('GroupModal', () => {
  it('does not render when closed', () => {
    render(
      <GroupModal
        open={false}
        editingGroupUser={{ user_id: 'u-1', username: 'alice' }}
        availableGroups={[]}
        selectedGroupIds={[]}
        onToggleGroup={jest.fn()}
        onCancel={jest.fn()}
        onSave={jest.fn()}
      />
    );

    expect(screen.queryByTestId('users-group-modal')).not.toBeInTheDocument();
  });

  it('renders selected groups and forwards actions', async () => {
    const user = userEvent.setup();
    const onToggleGroup = jest.fn();
    const onCancel = jest.fn();
    const onSave = jest.fn();

    render(
      <GroupModal
        open
        editingGroupUser={{ user_id: 'u-1', full_name: 'Alice', username: 'alice' }}
        availableGroups={[
          { group_id: 7, group_name: 'Default' },
          { group_id: 8, group_name: 'Ops', description: 'Ops tools' },
        ]}
        selectedGroupIds={[7]}
        onToggleGroup={onToggleGroup}
        onCancel={onCancel}
        onSave={onSave}
      />
    );

    expect(screen.getByTestId('users-group-modal')).toBeInTheDocument();
    expect(screen.getByRole('heading')).toHaveTextContent('Alice');
    expect(screen.getByText(/\b1\b/)).toBeInTheDocument();

    await user.click(screen.getByTestId('users-group-checkbox-8'));
    await user.click(screen.getByTestId('users-group-cancel'));
    await user.click(screen.getByTestId('users-group-save'));

    expect(onToggleGroup).toHaveBeenCalledWith(8, true);
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSave).toHaveBeenCalledTimes(1);
  });
});
