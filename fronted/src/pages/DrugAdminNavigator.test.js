import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import DrugAdminNavigator from './DrugAdminNavigator';
import drugAdminApi from '../features/drugAdmin/api';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('../features/drugAdmin/api', () => ({
  __esModule: true,
  default: {
    listProvinces: jest.fn(),
    resolveProvince: jest.fn(),
    verifyAll: jest.fn(),
  },
}));

describe('DrugAdminNavigator', () => {
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
      total: 1,
      success: 0,
      failed: 1,
      rows: [
        {
          province: '上海',
          ok: false,
          errors: ['timeout'],
        },
      ],
    });
    openSpy = jest.spyOn(window, 'open').mockImplementation(() => null);
  });

  afterEach(() => {
    openSpy.mockRestore();
  });

  it('loads provinces and routes open/verify actions through the feature API', async () => {
    const user = userEvent.setup();

    render(<DrugAdminNavigator />);

    expect(await screen.findByTestId('drug-admin-page')).toBeInTheDocument();
    await waitFor(() => expect(drugAdminApi.listProvinces).toHaveBeenCalledTimes(1));

    await user.click(screen.getByTestId('drug-admin-open-selected'));

    await waitFor(() => {
      expect(drugAdminApi.resolveProvince).toHaveBeenCalledWith('上海');
    });
    expect(openSpy).toHaveBeenCalledWith(
      'https://example.com/shanghai',
      '_blank',
      'noopener,noreferrer'
    );

    await user.click(screen.getByTestId('drug-admin-verify-all'));

    await waitFor(() => expect(drugAdminApi.verifyAll).toHaveBeenCalledTimes(1));
    expect(await screen.findByText('timeout')).toBeInTheDocument();
  });
});
