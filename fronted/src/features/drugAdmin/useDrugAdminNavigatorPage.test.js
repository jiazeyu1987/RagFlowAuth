import { act, renderHook, waitFor } from '@testing-library/react';
import drugAdminApi from './api';
import useDrugAdminNavigatorPage from './useDrugAdminNavigatorPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    listProvinces: jest.fn(),
    resolveProvince: jest.fn(),
    verifyAll: jest.fn(),
  },
}));

describe('useDrugAdminNavigatorPage', () => {
  let openSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    drugAdminApi.listProvinces.mockResolvedValue({
      validated_on: '2026-04-06T09:00:00Z',
      source: 'fixture',
      provinces: [
        { name: '上海' },
        { name: '北京' },
      ],
    });
    drugAdminApi.resolveProvince.mockResolvedValue({
      ok: true,
      url: 'https://example.com/shanghai',
      code: 200,
      errors: [],
    });
    drugAdminApi.verifyAll.mockResolvedValue({
      total: 2,
      success: 1,
      failed: 1,
      rows: [
        {
          province: '上海',
          ok: false,
          errors: ['timeout'],
        },
        {
          province: '北京',
          ok: true,
          errors: [],
        },
      ],
    });
    openSpy = jest.spyOn(window, 'open').mockImplementation(() => null);
  });

  afterEach(() => {
    openSpy.mockRestore();
  });

  it('loads province metadata into stable controller state', async () => {
    const { result } = renderHook(() => useDrugAdminNavigatorPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    expect(drugAdminApi.listProvinces).toHaveBeenCalledTimes(1);
    expect(result.current.selectedProvince).toBe('上海');
    expect(result.current.validatedOn).toBe('2026-04-06T09:00:00Z');
    expect(result.current.source).toBe('fixture');

    act(() => {
      result.current.goBack();
    });

    expect(mockNavigate).toHaveBeenCalledWith('/tools');
  });

  it('opens the selected province and exposes failed verify rows', async () => {
    const { result } = renderHook(() => useDrugAdminNavigatorPage());

    await waitFor(() => expect(result.current.loading).toBe(false));

    await act(async () => {
      await result.current.openSelected();
    });

    expect(drugAdminApi.resolveProvince).toHaveBeenCalledWith('上海');
    expect(openSpy).toHaveBeenCalledWith(
      'https://example.com/shanghai',
      '_blank',
      'noopener,noreferrer'
    );

    await act(async () => {
      await result.current.verifyAll();
    });

    expect(drugAdminApi.verifyAll).toHaveBeenCalledTimes(1);
    expect(result.current.failedRows).toEqual([
      expect.objectContaining({
        province: '上海',
      }),
    ]);
    expect(result.current.info).toContain('校验完成');
  });
});
