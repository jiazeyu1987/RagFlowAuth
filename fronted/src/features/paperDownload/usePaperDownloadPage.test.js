import { act, renderHook } from '@testing-library/react';

import { useAuth } from '../../hooks/useAuth';
import useDownloadPageController from '../download/useDownloadPageController';
import usePaperDownloadPage from './usePaperDownloadPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../download/useDownloadPageController', () => jest.fn());

describe('usePaperDownloadPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockReset();

    useAuth.mockReturnValue({
      canDownload: () => true,
    });

    useDownloadPageController.mockReturnValue({
      previewOpen: false,
      setPreviewOpen: jest.fn(),
      resultTab: 'current',
      setResultTab: jest.fn(),
      items: [],
      historyKeywords: [],
    });
  });

  it('exposes controller state plus page-level permission and back navigation', () => {
    const { result } = renderHook(() => usePaperDownloadPage());

    expect(result.current.canDownloadFiles).toBe(true);
    expect(result.current.resultTab).toBe('current');

    act(() => {
      result.current.handleBackToTools();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/tools');
  });

  it('disables downloads when auth permissions do not allow it', () => {
    useAuth.mockReturnValue({
      canDownload: () => false,
    });

    const { result } = renderHook(() => usePaperDownloadPage());

    expect(result.current.canDownloadFiles).toBe(false);
  });
});
