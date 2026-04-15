import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import QualitySystemConfig from './QualitySystemConfig';
import useQualitySystemConfigPage from '../features/qualitySystemConfig/useQualitySystemConfigPage';

jest.mock('../features/qualitySystemConfig/useQualitySystemConfigPage', () => jest.fn());
jest.mock('../features/qualitySystemConfig/components/QualitySystemUserMultiSelect', () => {
  return function MockQualitySystemUserMultiSelect({ selectedUsers, testIdPrefix }) {
    return (
      <div data-testid={`${testIdPrefix}-mock`}>
        {(selectedUsers || []).map((item) => item.user_id).join(',')}
      </div>
    );
  };
});

describe('QualitySystemConfig', () => {
  beforeEach(() => {
    window.prompt = jest.fn();
    window.confirm = jest.fn();
  });

  afterEach(() => {
    jest.resetAllMocks();
  });

  it('renders position assignments and saves with a change reason', async () => {
    const saveAssignments = jest.fn();
    useQualitySystemConfigPage.mockReturnValue({
      loading: false,
      error: '',
      notice: '',
      activeTab: 'positions',
      tabs: { positions: 'positions', categories: 'categories' },
      positions: [
        {
          id: 11,
          name: 'QA',
          in_signoff: true,
          in_compiler: false,
          in_approver: false,
          is_dirty: true,
          draft_assigned_users: [{ user_id: 'u-1', username: 'qa_user' }],
        },
      ],
      fileCategories: [],
      categoryName: '',
      categorySubmitting: false,
      deactivatingCategoryId: null,
      savingAssignments: {},
      setActiveTab: jest.fn(),
      setCategoryName: jest.fn(),
      updatePositionDraft: jest.fn(),
      saveAssignments,
      createCategory: jest.fn(),
      deactivateCategory: jest.fn(),
      searchUsers: jest.fn(),
    });
    window.prompt.mockReturnValue('Save reason');

    render(<QualitySystemConfig />);

    expect(screen.getByText('QA')).toBeInTheDocument();
    expect(screen.getByTestId('quality-system-config-position-users-11-mock')).toHaveTextContent('u-1');

    const user = userEvent.setup();
    await user.click(screen.getByTestId('quality-system-config-position-save-11'));

    expect(saveAssignments).toHaveBeenCalledWith(11, 'Save reason');
  });

  it('renders file categories and wires add/remove actions', async () => {
    const createCategory = jest.fn();
    const deactivateCategory = jest.fn();
    useQualitySystemConfigPage.mockReturnValue({
      loading: false,
      error: '',
      notice: '',
      activeTab: 'categories',
      tabs: { positions: 'positions', categories: 'categories' },
      positions: [],
      fileCategories: [
        { id: 7, name: '受控文件', seeded_from_json: true },
      ],
      categoryName: '新增文件小类',
      categorySubmitting: false,
      deactivatingCategoryId: null,
      savingAssignments: {},
      setActiveTab: jest.fn(),
      setCategoryName: jest.fn(),
      updatePositionDraft: jest.fn(),
      saveAssignments: jest.fn(),
      createCategory,
      deactivateCategory,
      searchUsers: jest.fn(),
    });
    window.prompt
      .mockReturnValueOnce('Create reason')
      .mockReturnValueOnce('Deactivate reason');
    window.confirm.mockReturnValue(true);

    render(<QualitySystemConfig />);

    const user = userEvent.setup();
    await user.click(screen.getByTestId('quality-system-config-category-add'));
    expect(createCategory).toHaveBeenCalledWith('Create reason');

    await user.click(screen.getByTestId('quality-system-config-category-remove-7'));
    expect(deactivateCategory).toHaveBeenCalledWith(7, 'Deactivate reason');
  });
});
