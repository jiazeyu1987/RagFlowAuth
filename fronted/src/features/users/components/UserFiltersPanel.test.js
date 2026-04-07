import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import UserFiltersPanel from './UserFiltersPanel';

const defaultProps = {
  filters: {
    q: '',
    company_id: '',
    department_id: '',
    status: '',
    group_id: '',
    assignment_status: '',
    created_from: '',
    created_to: '',
  },
  setFilters: jest.fn(),
  companies: [
    { id: 1, name: 'Acme' },
    { id: 2, name: 'Other' },
  ],
  departments: [
    { id: 11, name: 'QA', path_name: 'Acme / QA', company_id: 1 },
    { id: 12, name: 'IT', path_name: 'Other / IT', company_id: 2 },
  ],
  availableGroups: [{ group_id: 7, group_name: 'Default' }],
  permissionGroupsLoading: false,
  permissionGroupsError: null,
  isSubAdminUser: false,
  onGroupFilterFocus: jest.fn(),
  onResetFilters: jest.fn(),
};

describe('UserFiltersPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('shows all filter fields for admins', () => {
    render(<UserFiltersPanel {...defaultProps} />);

    expect(screen.getByTestId('users-filter-company')).toBeInTheDocument();
    expect(screen.getByTestId('users-filter-department')).toBeInTheDocument();
    expect(screen.getByTestId('users-filter-assignment-status')).toBeInTheDocument();
    expect(screen.getByTestId('users-filter-created-from')).toBeInTheDocument();
    expect(screen.getByTestId('users-filter-created-to')).toBeInTheDocument();
  });

  it('hides scoped filters for sub admins while keeping common filters', () => {
    render(<UserFiltersPanel {...defaultProps} isSubAdminUser />);

    expect(screen.getByTestId('users-filter-q')).toBeInTheDocument();
    expect(screen.getByTestId('users-filter-status')).toBeInTheDocument();
    expect(screen.getByTestId('users-filter-group')).toBeInTheDocument();
    expect(screen.getByTestId('users-filter-assignment-status')).toBeInTheDocument();
    expect(screen.getByTestId('users-filter-reset')).toBeInTheDocument();
    expect(screen.queryByTestId('users-filter-company')).not.toBeInTheDocument();
    expect(screen.queryByTestId('users-filter-department')).not.toBeInTheDocument();
    expect(screen.queryByTestId('users-filter-created-from')).not.toBeInTheDocument();
    expect(screen.queryByTestId('users-filter-created-to')).not.toBeInTheDocument();
  });

  it('renders the reset button in red', () => {
    render(<UserFiltersPanel {...defaultProps} />);

    expect(screen.getByTestId('users-filter-reset')).toHaveStyle({
      backgroundColor: '#dc2626',
      color: 'white',
    });
  });

  it('loads permission groups when the group filter receives focus', async () => {
    const user = userEvent.setup();
    render(<UserFiltersPanel {...defaultProps} />);

    await user.click(screen.getByTestId('users-filter-group'));

    expect(defaultProps.onGroupFilterFocus).toHaveBeenCalledTimes(1);
  });
});
