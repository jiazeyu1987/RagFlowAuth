import { renderHook } from '@testing-library/react';
import { useKnowledgeDirectoryModeReset } from './useKnowledgeDirectoryModeReset';

describe('useKnowledgeDirectoryModeReset', () => {
  it('resets state when no knowledge-directory mode remains active', () => {
    const resetKnowledgeDirectoryState = jest.fn();

    renderHook(() =>
      useKnowledgeDirectoryModeReset({
        createMode: {
          isOpen: false,
          userType: 'normal',
        },
        policyMode: {
          isOpen: false,
          userType: 'normal',
        },
        resetKnowledgeDirectoryState,
      })
    );

    expect(resetKnowledgeDirectoryState).toHaveBeenCalledTimes(1);
  });

  it('does not reset while a sub-admin knowledge-directory mode is active', () => {
    const resetKnowledgeDirectoryState = jest.fn();

    renderHook(() =>
      useKnowledgeDirectoryModeReset({
        createMode: {
          isOpen: true,
          userType: 'sub_admin',
        },
        policyMode: {
          isOpen: false,
          userType: 'normal',
        },
        resetKnowledgeDirectoryState,
      })
    );

    expect(resetKnowledgeDirectoryState).not.toHaveBeenCalled();
  });
});
