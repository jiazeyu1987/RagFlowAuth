import { act, renderHook } from '@testing-library/react';

import useMobileBreakpoint from './useMobileBreakpoint';

describe('useMobileBreakpoint', () => {
  const originalInnerWidth = window.innerWidth;

  afterEach(() => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: originalInnerWidth,
    });
  });

  it('derives the initial mobile flag from the current viewport width', () => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: 640,
    });

    const { result } = renderHook(() => useMobileBreakpoint(768));

    expect(result.current).toBe(true);
  });

  it('updates when the viewport crosses the breakpoint', () => {
    Object.defineProperty(window, 'innerWidth', {
      configurable: true,
      writable: true,
      value: 1024,
    });

    const { result } = renderHook(() => useMobileBreakpoint(768));

    expect(result.current).toBe(false);

    act(() => {
      window.innerWidth = 640;
      window.dispatchEvent(new Event('resize'));
    });

    expect(result.current).toBe(true);
  });
});
