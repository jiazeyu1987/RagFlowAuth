import { renderHook } from '@testing-library/react';
import { useKnowledgeDirectoryModeLoader } from './useKnowledgeDirectoryModeLoader';

describe('useKnowledgeDirectoryModeLoader', () => {
  it('loads directories when the mode is open for a sub admin user', () => {
    const loadKnowledgeDirectories = jest.fn();

    renderHook(() =>
      useKnowledgeDirectoryModeLoader({
        companyId: '2',
        isOpen: true,
        userType: 'sub_admin',
        loadKnowledgeDirectories,
      })
    );

    expect(loadKnowledgeDirectories).toHaveBeenCalledWith('2');
  });

  it('does not load directories when the mode is inactive', () => {
    const loadKnowledgeDirectories = jest.fn();

    renderHook(() =>
      useKnowledgeDirectoryModeLoader({
        companyId: '2',
        isOpen: true,
        userType: 'normal',
        loadKnowledgeDirectories,
      })
    );

    expect(loadKnowledgeDirectories).not.toHaveBeenCalled();
  });
});
