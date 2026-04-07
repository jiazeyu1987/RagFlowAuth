import React from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import DisableAccountSection from './DisableAccountSection';

describe('DisableAccountSection', () => {
  const inputStyle = {
    width: '100%',
    padding: '10px 12px',
    border: '1px solid #d1d5db',
    borderRadius: '4px',
    boxSizing: 'border-box',
  };

  it('renders always-enabled schedule fields', async () => {
    const user = userEvent.setup();
    const onChangeMode = jest.fn();
    const onChangeUntilDate = jest.fn();

    render(
      <DisableAccountSection
        enabled
        mode="until"
        untilDate="2026-04-09"
        onChangeMode={onChangeMode}
        onChangeUntilDate={onChangeUntilDate}
        radioName="disable-modal"
        immediateTestId="disable-immediate"
        untilTestId="disable-until"
        dateTestId="disable-date"
        inputStyle={inputStyle}
      />
    );

    expect(screen.getByTestId('disable-date')).toHaveValue('2026-04-09');
    await user.click(screen.getByTestId('disable-immediate'));
    fireEvent.change(screen.getByTestId('disable-date'), { target: { value: '2026-04-10' } });

    expect(onChangeMode).toHaveBeenCalledWith('immediate');
    expect(onChangeUntilDate).toHaveBeenCalledWith('2026-04-10');
  });

  it('renders the enabled toggle when requested', async () => {
    const user = userEvent.setup();
    const onToggleEnabled = jest.fn();

    render(
      <DisableAccountSection
        enabled={false}
        mode="immediate"
        untilDate=""
        onChangeMode={jest.fn()}
        onChangeUntilDate={jest.fn()}
        showEnabledToggle
        onToggleEnabled={onToggleEnabled}
        enabledTestId="disable-enabled"
        radioName="policy-modal"
        immediateTestId="policy-immediate"
        untilTestId="policy-until"
        dateTestId="policy-date"
        inputStyle={inputStyle}
      />
    );

    expect(screen.queryByTestId('policy-immediate')).not.toBeInTheDocument();
    await user.click(screen.getByTestId('disable-enabled'));
    expect(onToggleEnabled).toHaveBeenCalledWith(true);
  });
});
