import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import CreateUserModal from './CreateUserModal';
import { orgDirectoryApi } from '../../../orgDirectory/api';

jest.mock('../../../../shared/hooks/useMobileBreakpoint', () => jest.fn(() => false));

jest.mock('../../../orgDirectory/api', () => ({
  orgDirectoryApi: {
    getTree: jest.fn(),
  },
}));

const ORG_TREE = [
  {
    id: 2,
    node_type: 'company',
    name: '\u5176\u4ed6\u516c\u53f8',
    children: [
      {
        id: 22,
        node_type: 'department',
        name: '\u7814\u53d1\u90e8',
        path_name: '\u5176\u4ed6\u516c\u53f8 / \u7814\u53d1\u90e8',
        children: [
          {
            id: 1001,
            node_type: 'person',
            name: '\u738b\u5c0f\u660e',
            employee_user_id: 'wangxiaoming',
            company_id: 2,
            department_id: 22,
            children: [],
          },
          {
            id: 1002,
            node_type: 'person',
            name: '\u674e\u56db',
            employee_user_id: 'lisi',
            company_id: 2,
            department_id: 22,
            children: [],
          },
        ],
      },
    ],
  },
];

const ORG_TREE_WITH_NULL_DEPARTMENT = [
  {
    id: 2,
    node_type: 'company',
    name: '\u5176\u4ed6\u516c\u53f8',
    children: [
      {
        id: 22,
        node_type: 'department',
        name: '\u7814\u53d1\u90e8',
        path_name: '\u5176\u4ed6\u516c\u53f8 / \u7814\u53d1\u90e8',
        children: [
          {
            id: 1003,
            node_type: 'person',
            name: '\u738b\u6b46',
            employee_user_id: 'wangxin',
            company_id: 2,
            department_id: null,
            children: [],
          },
        ],
      },
    ],
  },
];

const ORG_TREE_WITH_PINYIN_EDGE_CASES = [
  {
    id: 2,
    node_type: 'company',
    name: '\u5176\u4ed6\u516c\u53f8',
    children: [
      {
        id: 22,
        node_type: 'department',
        name: '\u7814\u53d1\u90e8',
        path_name: '\u5176\u4ed6\u516c\u53f8 / \u7814\u53d1\u90e8',
        children: [
          {
            id: 1004,
            node_type: 'person',
            name: '\u66fe\u4e50\u4e50',
            employee_user_id: 'zenglele-001',
            company_id: 2,
            department_id: 22,
            children: [],
          },
          {
            id: 1005,
            node_type: 'person',
            name: 'A\u5f20-\u4e09 007',
            employee_user_id: 'mixed-007',
            company_id: 2,
            department_id: 22,
            children: [],
          },
        ],
      },
    ],
  },
];

const buildLargeWangOrgTree = () => {
  const wangPeople = Array.from({ length: 12 }, (_, index) => ({
    id: 2000 + index,
    node_type: 'person',
    name: `\u738b\u540c\u4e8b${index + 1}`,
    employee_user_id: `wang-${index + 1}`,
    company_id: 2,
    department_id: 22,
    children: [],
  }));

  wangPeople.push({
    id: 2999,
    node_type: 'person',
    name: '\u738b\u6b23',
    employee_user_id: 'wangxin-special',
    company_id: 2,
    department_id: 22,
    children: [],
  });

  return [
    {
      id: 2,
      node_type: 'company',
      name: '\u5176\u4ed6\u516c\u53f8',
      children: [
        {
          id: 22,
          node_type: 'department',
          name: '\u7814\u53d1\u90e8',
          path_name: '\u5176\u4ed6\u516c\u53f8 / \u7814\u53d1\u90e8',
          children: wangPeople,
        },
      ],
    },
  ];
};

function CreateModalHarness({ allUsers = [] }) {
  const [newUser, setNewUser] = React.useState({
    full_name: '',
    username: '',
    employee_user_id: '',
    password: '111111',
    user_type: 'normal',
    manager_user_id: 'sub-1',
    managed_kb_root_node_id: '',
    company_id: '19',
    department_id: '',
    group_ids: [],
    tool_ids: [],
    max_login_sessions: 3,
    idle_timeout_minutes: 120,
  });

  const onFieldChange = React.useCallback((field, value) => {
    setNewUser((previous) => ({ ...previous, [field]: value }));
  }, []);

  return (
    <>
      <CreateUserModal
        open
        newUser={newUser}
        error={null}
        allUsers={allUsers}
        companies={[
          { id: 19, name: '\u745b\u6cf0\u533b\u7597' },
          { id: 2, name: '\u5176\u4ed6\u516c\u53f8' },
        ]}
        departments={[
          {
            id: 22,
            company_id: 2,
            name: '\u7814\u53d1\u90e8',
            path_name: '\u5176\u4ed6\u516c\u53f8 / \u7814\u53d1\u90e8',
          },
        ]}
        subAdminOptions={[
          { value: 'sub-1', label: '\u5b50\u7ba1\u7406\u5458A', username: 'sub_admin_a' },
        ]}
        availableTools={[]}
        kbDirectoryNodes={[]}
        kbDirectoryLoading={false}
        kbDirectoryError={null}
        kbDirectoryCreateError={null}
        kbDirectoryCreatingRoot={false}
        orgDirectoryError={null}
        onSubmit={(event) => event.preventDefault()}
        onCancel={jest.fn()}
        onFieldChange={onFieldChange}
        onToggleTool={jest.fn()}
        onCreateRootDirectory={jest.fn()}
      />
      <div data-testid="draft-employee-user-id">{newUser.employee_user_id}</div>
    </>
  );
}

describe('CreateUserModal employee dropdown binding', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    orgDirectoryApi.getTree.mockResolvedValue(ORG_TREE);
  });

  it('binds employee only through full-name dropdown selection', async () => {
    const user = userEvent.setup();
    render(<CreateModalHarness />);

    const fullNameInput = screen.getByTestId('users-create-full-name');
    await user.click(fullNameInput);
    await user.type(fullNameInput, '\u738b');

    await waitFor(() => expect(orgDirectoryApi.getTree).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId('users-create-full-name-result-wangxiaoming')).toBeInTheDocument();
    expect(screen.getByTestId('draft-employee-user-id')).toHaveTextContent('');
  });

  it('autofills username from selected employee full name when username is blank', async () => {
    const user = userEvent.setup();
    render(<CreateModalHarness />);

    const fullNameInput = screen.getByTestId('users-create-full-name');
    await user.click(fullNameInput);
    await user.type(fullNameInput, '\u738b');
    await user.click(await screen.findByTestId('users-create-full-name-result-wangxiaoming'));

    expect(screen.getByTestId('users-create-username')).toHaveValue('wangxiaoming');
    expect(screen.getByTestId('draft-employee-user-id')).toHaveTextContent('wangxiaoming');
    expect(screen.getByTestId('users-create-company')).toHaveValue('2');
    expect(screen.getByTestId('users-create-department')).toHaveValue('22');
  });

  it('keeps username editable and autofills organization fields after selecting employee', async () => {
    const user = userEvent.setup();
    render(<CreateModalHarness />);

    await user.type(screen.getByTestId('users-create-username'), 'friendly_account');
    const fullNameInput = screen.getByTestId('users-create-full-name');
    await user.click(fullNameInput);
    await user.type(fullNameInput, '\u738b');

    const option = await screen.findByTestId('users-create-full-name-result-wangxiaoming');
    await user.click(option);

    expect(screen.getByTestId('users-create-username')).toHaveValue('friendly_account');
    expect(screen.getByTestId('draft-employee-user-id')).toHaveTextContent('wangxiaoming');
    expect(screen.getByTestId('users-create-full-name')).toHaveValue('\u738b\u5c0f\u660e');
    expect(screen.getByTestId('users-create-company')).toHaveValue('2');
    expect(screen.getByTestId('users-create-department')).toHaveValue('22');
    expect(screen.getByTestId('users-create-company')).toBeDisabled();
    expect(screen.getByTestId('users-create-department')).toBeDisabled();
  });

  it('replaces the prior auto-generated username when the selected employee changes', async () => {
    const user = userEvent.setup();
    render(<CreateModalHarness />);

    const fullNameInput = screen.getByTestId('users-create-full-name');

    await user.click(fullNameInput);
    await user.type(fullNameInput, '\u738b');
    await user.click(await screen.findByTestId('users-create-full-name-result-wangxiaoming'));
    expect(screen.getByTestId('users-create-username')).toHaveValue('wangxiaoming');

    await user.clear(fullNameInput);
    await user.type(fullNameInput, '\u674e');
    await user.click(await screen.findByTestId('users-create-full-name-result-lisi'));

    expect(screen.getByTestId('users-create-username')).toHaveValue('lisi');
    expect(screen.getByTestId('draft-employee-user-id')).toHaveTextContent('lisi');
  });

  it('autofills surname polyphone names with surname-aware pinyin', async () => {
    const user = userEvent.setup();
    orgDirectoryApi.getTree.mockResolvedValueOnce(ORG_TREE_WITH_PINYIN_EDGE_CASES);
    render(<CreateModalHarness />);

    const fullNameInput = screen.getByTestId('users-create-full-name');
    await user.click(fullNameInput);
    await user.type(fullNameInput, '\u66fe');
    await user.click(await screen.findByTestId('users-create-full-name-result-zenglele-001'));

    expect(screen.getByTestId('users-create-username')).toHaveValue('zenglele');
  });

  it('strips non alphanumeric characters when building usernames from mixed names', async () => {
    const user = userEvent.setup();
    orgDirectoryApi.getTree.mockResolvedValueOnce(ORG_TREE_WITH_PINYIN_EDGE_CASES);
    render(<CreateModalHarness />);

    const fullNameInput = screen.getByTestId('users-create-full-name');
    await user.click(fullNameInput);
    await user.type(fullNameInput, '007');
    await user.click(await screen.findByTestId('users-create-full-name-result-mixed-007'));

    expect(screen.getByTestId('users-create-username')).toHaveValue('azhangsan007');
  });

  it('allows selecting employee without department by filling company default department', async () => {
    const user = userEvent.setup();
    orgDirectoryApi.getTree.mockResolvedValueOnce(ORG_TREE_WITH_NULL_DEPARTMENT);
    render(<CreateModalHarness />);

    const fullNameInput = screen.getByTestId('users-create-full-name');
    await user.click(fullNameInput);
    await user.type(fullNameInput, '\u738b\u6b46');

    const option = await screen.findByTestId('users-create-full-name-result-wangxin');
    await user.click(option);

    expect(screen.getByTestId('draft-employee-user-id')).toHaveTextContent('wangxin');
    expect(screen.getByTestId('users-create-company')).toHaveValue('2');
    expect(screen.getByTestId('users-create-department')).toHaveValue('22');
  });

  it('hides employees whose employee_user_id is already bound by another user', async () => {
    const user = userEvent.setup();
    render(
      <CreateModalHarness
        allUsers={[{ user_id: 'u-1', username: 'old_alias', employee_user_id: 'wangxiaoming' }]}
      />
    );

    const fullNameInput = screen.getByTestId('users-create-full-name');
    await user.click(fullNameInput);

    await waitFor(() => expect(orgDirectoryApi.getTree).toHaveBeenCalledTimes(1));
    expect(screen.queryByTestId('users-create-full-name-result-wangxiaoming')).not.toBeInTheDocument();
    expect(screen.getByTestId('users-create-full-name-result-lisi')).toBeInTheDocument();
  });

  it('clears employee binding when selected full name is edited again', async () => {
    const user = userEvent.setup();
    render(<CreateModalHarness />);

    const fullNameInput = screen.getByTestId('users-create-full-name');
    await user.click(fullNameInput);
    await user.type(fullNameInput, '\u738b');
    await user.click(await screen.findByTestId('users-create-full-name-result-wangxiaoming'));
    expect(screen.getByTestId('draft-employee-user-id')).toHaveTextContent('wangxiaoming');

    await user.type(fullNameInput, 'A');
    expect(screen.getByTestId('draft-employee-user-id')).toHaveTextContent('');
  });

  it('does not truncate fuzzy results so later matches remain selectable', async () => {
    const user = userEvent.setup();
    orgDirectoryApi.getTree.mockResolvedValueOnce(buildLargeWangOrgTree());
    render(<CreateModalHarness />);

    const fullNameInput = screen.getByTestId('users-create-full-name');
    await user.click(fullNameInput);
    await user.type(fullNameInput, '\u738b');

    await waitFor(() => expect(orgDirectoryApi.getTree).toHaveBeenCalledTimes(1));
    expect(screen.getByTestId('users-create-full-name-result-wang-12')).toBeInTheDocument();
    expect(screen.getByTestId('users-create-full-name-result-wangxin-special')).toBeInTheDocument();
  });
});
