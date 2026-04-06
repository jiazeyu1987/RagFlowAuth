import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import NMPATool from './NMPATool';
import { NMPA_CATALOG_URL, NMPA_HOME_URL } from '../features/drugAdmin/useNmpaToolPage';

const mockNavigate = jest.fn();

jest.mock('react-router-dom', () => {
  const actual = jest.requireActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

describe('NMPATool', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockNavigate.mockReset();
  });

  it('navigates back to the tools page', async () => {
    const user = userEvent.setup();

    render(<NMPATool />);

    await user.click(screen.getByTestId('nmpa-back-btn'));

    expect(mockNavigate).toHaveBeenCalledWith('/tools');
  });

  it('opens external NMPA links from the page', async () => {
    const user = userEvent.setup();
    const openSpy = jest.spyOn(window, 'open').mockImplementation(() => null);

    render(<NMPATool />);

    await user.click(screen.getByTestId('nmpa-home-btn'));
    await user.click(screen.getByTestId('nmpa-catalog-btn'));

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
