import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ResetPasswordModal from './ResetPasswordModal';

jest.mock('../../../../shared/hooks/useMobileBreakpoint', () => jest.fn(() => false));

describe('ResetPasswordModal', () => {
  it('does not render when closed', () => {
    render(
      <ResetPasswordModal
        open={false}
        user={{ user_id: 'u-1', username: 'alice' }}
        value=""
        confirm=""
        error=""
        submitting={false}
        onChangeValue={jest.fn()}
        onChangeConfirm={jest.fn()}
        onCancel={jest.fn()}
        onSubmit={jest.fn()}
      />
    );

    expect(screen.queryByTestId('users-reset-password-modal')).not.toBeInTheDocument();
  });

  it('renders fields and forwards change and action handlers', async () => {
    const user = userEvent.setup();
    const onChangeValue = jest.fn();
    const onChangeConfirm = jest.fn();
    const onCancel = jest.fn();
    const onSubmit = jest.fn();

    render(
      <ResetPasswordModal
        open
        user={{ user_id: 'u-1', full_name: 'Alice', username: 'alice' }}
        value=""
        confirm=""
        error="mismatch"
        submitting={false}
        onChangeValue={onChangeValue}
        onChangeConfirm={onChangeConfirm}
        onCancel={onCancel}
        onSubmit={onSubmit}
      />
    );

    expect(screen.getByRole('heading')).toHaveTextContent('Alice');
    expect(screen.getByTestId('users-reset-password-error')).toHaveTextContent('mismatch');

    await user.type(screen.getByTestId('users-reset-password-new'), 'Password1');
    await user.type(screen.getByTestId('users-reset-password-confirm'), 'Password1');
    await user.click(screen.getByTestId('users-reset-password-cancel'));
    await user.click(screen.getByTestId('users-reset-password-save'));

    expect(onChangeValue).toHaveBeenCalled();
    expect(onChangeConfirm).toHaveBeenCalled();
    expect(onCancel).toHaveBeenCalledTimes(1);
    expect(onSubmit).toHaveBeenCalledTimes(1);
  });
});
