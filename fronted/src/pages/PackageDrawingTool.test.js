import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PackageDrawingTool from './PackageDrawingTool';
import packageDrawingApi from '../features/packageDrawing/api';
import { useAuth } from '../hooks/useAuth';

jest.mock('../features/packageDrawing/api', () => ({
  __esModule: true,
  default: {
    queryByModel: jest.fn(),
    importExcel: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('PackageDrawingTool', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      isAdmin: () => true,
    });
    packageDrawingApi.queryByModel.mockResolvedValue({
      model: 'M-001',
      barcode: 'BC-001',
      parameters: { Spec: 'A1' },
      images: [],
    });
    packageDrawingApi.importExcel.mockResolvedValue({
      rows_scanned: 2,
      total: 1,
      success: 1,
      failed: 0,
      errors: [],
    });
  });

  it('queries model details and imports an xlsx file through the feature API', async () => {
    const user = userEvent.setup();

    render(<PackageDrawingTool />);

    await user.type(screen.getByTestId('package-drawing-query-model'), 'M-001');
    await user.click(screen.getByTestId('package-drawing-query-submit'));

    await waitFor(() => {
      expect(packageDrawingApi.queryByModel).toHaveBeenCalledWith('M-001');
    });
    expect(await screen.findByTestId('package-drawing-query-result')).toBeInTheDocument();

    await user.click(screen.getByTestId('package-drawing-tab-import'));
    const file = new File(['xlsx'], 'demo.xlsx', {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    await user.upload(screen.getByTestId('package-drawing-import-file'), file);
    await user.click(screen.getByTestId('package-drawing-import-submit'));

    await waitFor(() => {
      expect(packageDrawingApi.importExcel).toHaveBeenCalledWith(file);
    });
    expect(await screen.findByTestId('package-drawing-import-summary')).toBeInTheDocument();
  });
});
