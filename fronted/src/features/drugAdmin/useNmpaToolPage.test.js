import { act, renderHook } from '@testing-library/react';

import useNmpaToolPage, { NMPA_CATALOG_URL, NMPA_HOME_URL } from './useNmpaToolPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('useNmpaToolPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockReset();
  });

  it('navigates back to the tools page', () => {
    const { result } = renderHook(() => useNmpaToolPage());

    act(() => {
      result.current.handleBack();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/tools');
  });

  it('opens the NMPA home page and catalog in a new tab', () => {
    const openSpy = jest.spyOn(window, 'open').mockImplementation(() => null);
    const { result } = renderHook(() => useNmpaToolPage());

    act(() => {
      result.current.handleOpenHome();
      result.current.handleOpenCatalog();
    });

    expect(openSpy).toHaveBeenNthCalledWith(
      1,
      NMPA_HOME_URL,
      '_blank',
      'noopener,noreferrer'
    );
    expect(openSpy).toHaveBeenNthCalledWith(
      2,
      NMPA_CATALOG_URL,
      '_blank',
      'noopener,noreferrer'
    );

    openSpy.mockRestore();
  });
});
