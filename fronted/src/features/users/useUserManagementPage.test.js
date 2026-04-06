import { act, renderHook } from '@testing-library/react';

import useUserManagementPage from './useUserManagementPage';
import { useUserManagement } from './hooks/useUserManagement';

jest.mock('./hooks/useUserManagement', () => ({
  useUserManagement: jest.fn(),
}));

const buildManagementState = (overrides = {}) => ({
  loading: false,
  error: null,
  canCreateUsers: true,
  handleOpenCreateModal: jest.fn(),
  ...overrides,
});

describe('useUserManagementPage', () => {
  const originalInnerWidth = window.innerWidth;

  beforeEach(() => {
    jest.clearAllMocks();
    useUserManagement.mockReturnValue(buildManagementState());
  });

  afterEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: originalInnerWidth,
    });
  });

  it('adds responsive page state while preserving the feature hook contract', () => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: 640,
    });

    const { result } = renderHook(() => useUserManagementPage());

    expect(result.current.isMobile).toBe(true);
    expect(result.current.canCreateUsers).toBe(true);
    expect(result.current.handleOpenCreateModal).toBeDefined();
  });

  it('updates the mobile flag when the viewport crosses the breakpoint', () => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: 1024,
    });

    const { result } = renderHook(() => useUserManagementPage());

    expect(result.current.isMobile).toBe(false);

    act(() => {
      window.innerWidth = 640;
      window.dispatchEvent(new Event('resize'));
    });

    expect(result.current.isMobile).toBe(true);
  });
});
