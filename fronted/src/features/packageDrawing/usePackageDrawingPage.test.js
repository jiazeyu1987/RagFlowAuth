import { act, renderHook, waitFor } from '@testing-library/react';
import usePackageDrawingPage from './usePackageDrawingPage';
import packageDrawingApi from './api';
import { useAuth } from '../../hooks/useAuth';

jest.mock('./api', () => ({
  __esModule: true,
  default: {
    queryByModel: jest.fn(),
    importExcel: jest.fn(),
  },
}));

jest.mock('../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('usePackageDrawingPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      isAdmin: () => true,
    });
    packageDrawingApi.queryByModel.mockResolvedValue({
      model: 'M-001',
      barcode: 'BC-001',
      parameters: { Spec: 'A1' },
      images: [{ data_url: 'data:image/png;base64,abc' }],
    });
    packageDrawingApi.importExcel.mockResolvedValue({
      rows_scanned: 2,
      total: 1,
      success: 1,
      failed: 0,
      errors: [],
    });
  });

  it('queries package drawing details with the trimmed model and exposes derived result data', async () => {
    const { result } = renderHook(() => usePackageDrawingPage());

    await act(async () => {
      result.current.setModel('  M-001  ');
    });

    await act(async () => {
      await result.current.handleQuerySubmit();
    });

    await waitFor(() => {
      expect(packageDrawingApi.queryByModel).toHaveBeenCalledWith('M-001');
    });
    expect(result.current.queryResult).toEqual(
      expect.objectContaining({
        model: 'M-001',
        barcode: 'BC-001',
      })
    );
    expect(result.current.resultParameters).toEqual([['Spec', 'A1']]);
    expect(result.current.resultImages).toEqual([{ data_url: 'data:image/png;base64,abc' }]);
  });

  it('imports the selected xlsx file through the feature api', async () => {
    const { result } = renderHook(() => usePackageDrawingPage());
    const file = new File(['xlsx'], 'demo.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });

    await act(async () => {
      result.current.handleImportFileChange(file);
    });

    await act(async () => {
      result.current.handleImportSubmit();
    });

    await waitFor(() => {
      expect(packageDrawingApi.importExcel).toHaveBeenCalledWith(file);
    });
    expect(result.current.importResult).toEqual(
      expect.objectContaining({
        rows_scanned: 2,
        total: 1,
      })
    );
  });
});
