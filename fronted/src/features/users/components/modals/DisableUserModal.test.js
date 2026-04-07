import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DisableUserModal from './DisableUserModal';

jest.mock('../../../../shared/hooks/useMobileBreakpoint', () => jest.fn(() => false));

describe('DisableUserModal', () => {
  it('does not render when user context is missing', () => {
    render(
      <DisableUserModal
        open
        user={null}
        mode="immediate"
        untilDate=""
        error=""
        submitting={false}
        onChangeMode={jest.fn()}
        onChangeUntilDate={jest.fn()}
        onCancel={jest.fn()}
        onConfirm={jest.fn()}
      />
    );

    expect(screen.queryByTestId('users-disable-modal')).not.toBeInTheDocument();
  });

  it('renders the disable options and forwards callbacks', async () => {
    const user = userEvent.setup();
    const onChangeMode = jest.fn();
    const onChangeUntilDate = jest.fn();
    const onCancel = jest.fn();
    const onConfirm = jest.fn();

    render(
      <DisableUserModal
        open
        user={{ user_id: 'u-1', full_name: 'Alice', username: 'alice' }}
        mode="until"
        untilDate="2026-04-08"
        error="date required"
        submitting={false}
        onChangeMode={onChangeMode}
        onChangeUntilDate={onChangeUntilDate}
        onCancel={onCancel}
        onConfirm={onConfirm}
      />
    );

    expect(screen.getByRole('heading')).toHaveTextContent('Alice');
    expect(screen.getByTestId('users-disable-until-date')).toHaveValue('2026-04-08');
    expect(screen.getByTestId('users-disable-error')).toHaveTextContent('date required');

    await user.click(screen.getByTestId('users-disable-mode-immediate'));
    fireEvent.change(screen.getByTestId('users-disable-until-date'), { target: { value: '2026-04-10' } });
    await user.click(screen.getByTestId('users-disable-cancel'));
    await user.click(screen.getByTestId('users-disable-confirm'));

    expect(onChangeMode).toHaveBeenCalledWith('immediate');
    expect(onChangeUntilDate).toHaveBeenCalledWith('2026-04-10');
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});
