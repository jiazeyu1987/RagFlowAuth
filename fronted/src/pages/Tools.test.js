import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import Tools from './Tools';
import drugAdminApi from '../features/drugAdmin/api';
import { useAuth } from '../hooks/useAuth';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
}));

jest.mock('../features/drugAdmin/api', () => ({
  __esModule: true,
  default: {
    listProvinces: jest.fn(),
  },
}));

jest.mock('../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

describe('Tools', () => {
  let openSpy;

  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      isAdmin: () => false,
      canAccessTool: () => true,
    });
    drugAdminApi.listProvinces.mockResolvedValue({
      provinces: [
        {
          name: '上海',
          urls: ['https://example.com/shanghai'],
        },
      ],
    });
    openSpy = jest.spyOn(window, 'open').mockImplementation(() => null);
  });

  afterEach(() => {
    openSpy.mockRestore();
  });

  it('loads province tools via the feature API and opens the selected province link', async () => {
    const user = userEvent.setup();

    render(<Tools />);

    const provinceCard = await screen.findByTestId('tool-card-drug_admin_上海');
    expect(drugAdminApi.listProvinces).toHaveBeenCalledTimes(1);

    await user.click(provinceCard);

    await waitFor(() => {
      expect(openSpy).toHaveBeenCalledWith(
        'https://example.com/shanghai',
        '_blank',
        'noopener,noreferrer'
      );
    });
  });
});
