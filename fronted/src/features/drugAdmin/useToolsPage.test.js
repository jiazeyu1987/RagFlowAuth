import { act, renderHook, waitFor } from '@testing-library/react';
import { useAuth } from '../../hooks/useAuth';
import drugAdminApi from './api';
import useToolsPage from './useToolsPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    listProvinces: jest.fn(),
  },
}));

const buildProvinceTools = (provinces) => (
  (Array.isArray(provinces) ? provinces : []).map((province) => ({
    id: `province-${province.name}`,
    permissionKey: 'drug_admin',
    name: province.name,
    href: province.urls[0],
  }))
);

describe('useToolsPage', () => {
  let openSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      isAdmin: () => false,
      canAccessTool: () => true,
    });
    drugAdminApi.listProvinces.mockResolvedValue({
      provinces: [],
    });
    openSpy = jest.spyOn(window, 'open').mockImplementation(() => null);
  });

  afterEach(() => {
    openSpy.mockRestore();
  });

  it('loads province tools into the controller and opens external links', async () => {
    drugAdminApi.listProvinces.mockResolvedValueOnce({
      provinces: [
        {
          name: '上海',
          urls: ['https://example.com/shanghai'],
        },
      ],
    });

    const { result } = renderHook(() => useToolsPage({
      baseTools: [
        {
          id: 'paper_download',
          route: '/tools/paper-download',
        },
      ],
      buildProvinceTools,
    }));

    await waitFor(() => {
      expect(result.current.pageItems.map((tool) => tool.id)).toEqual(
        expect.arrayContaining(['paper_download', 'province-上海'])
      );
    });

    act(() => {
      result.current.openTool(
        result.current.pageItems.find((tool) => tool.id === 'province-上海')
      );
    });

    expect(openSpy).toHaveBeenCalledWith(
      'https://example.com/shanghai',
      '_blank',
      'noopener,noreferrer'
    );
  });

  it('filters tools by permission and paginates routed tools through the controller', async () => {
    useAuth.mockReturnValue({
      isAdmin: () => true,
      canAccessTool: (permissionKey) => permissionKey !== 'blocked',
    });

    const baseTools = [
      { id: 'tool-1', route: '/tools/1' },
      { id: 'tool-2', route: '/tools/2' },
      { id: 'blocked', route: '/tools/blocked' },
      { id: 'tool-3', route: '/tools/3' },
      { id: 'tool-4', route: '/tools/4' },
    ];

    const { result } = renderHook(() => useToolsPage({
      baseTools,
      buildProvinceTools,
      pageSize: 2,
    }));

    await waitFor(() => expect(result.current.pageCount).toBe(3));

    expect(result.current.visibleTools.map((tool) => tool.id)).toEqual([
      'nas_browser',
      'tool-1',
      'tool-2',
      'tool-3',
      'tool-4',
    ]);
    expect(result.current.pageItems.map((tool) => tool.id)).toEqual([
      'nas_browser',
      'tool-1',
    ]);

    act(() => {
      result.current.goNextPage();
    });

    expect(result.current.safePage).toBe(2);
    expect(result.current.pageItems.map((tool) => tool.id)).toEqual([
      'tool-2',
      'tool-3',
    ]);

    act(() => {
      result.current.openTool(result.current.pageItems[0]);
    });

    expect(mockNavigate).toHaveBeenCalledWith('/tools/2');
  });
});
