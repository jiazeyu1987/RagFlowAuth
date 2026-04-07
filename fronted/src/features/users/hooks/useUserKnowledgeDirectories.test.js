import { act, renderHook, waitFor } from '@testing-library/react';
import { knowledgeApi } from '../../knowledge/api';
import { useUserKnowledgeDirectories } from './useUserKnowledgeDirectories';

jest.mock('../../knowledge/api', () => ({
  knowledgeApi: {
    listKnowledgeDirectories: jest.fn(),
    createKnowledgeDirectory: jest.fn(),
  },
}));

const baseOptions = () => ({
  isAdminUser: true,
  createMode: {
    isOpen: false,
    userType: 'normal',
    companyId: '',
    onRootCreated: jest.fn(),
  },
  policyMode: {
    isOpen: false,
    userType: 'normal',
    companyId: '',
    selectedManagedKbRootNodeId: '',
    onRootCreated: jest.fn(),
  },
  policyUser: null,
  mapErrorMessage: (message) => `mapped:${message}`,
  companyRequiredMessage: 'company-required',
  nameRequiredMessage: 'name-required',
  loadErrorMessage: 'load-error',
  createErrorMessage: 'create-error',
});

describe('useUserKnowledgeDirectories', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    knowledgeApi.listKnowledgeDirectories.mockResolvedValue({
      nodes: [{ id: 'node-1', name: 'Root', parent_id: null, path: '/Root' }],
    });
    knowledgeApi.createKnowledgeDirectory.mockResolvedValue({ id: 'node-created' });
  });

  it('loads directories when create mode opens for a sub admin draft', async () => {
    const options = {
      ...baseOptions(),
      createMode: {
        isOpen: true,
        userType: 'sub_admin',
        companyId: '2',
        onRootCreated: jest.fn(),
      },
    };
    const { result } = renderHook(() => useUserKnowledgeDirectories(options));

    await waitFor(() =>
      expect(knowledgeApi.listKnowledgeDirectories).toHaveBeenCalledWith({ companyId: 2 })
    );
    await waitFor(() =>
      expect(result.current.kbDirectoryNodes).toEqual([
        { id: 'node-1', name: 'Root', parent_id: null, path: '/Root' },
      ])
    );
    expect(result.current.kbDirectoryError).toBeNull();
  });

  it('creates a root directory, reloads directories, and forwards the created node id', async () => {
    const onRootCreated = jest.fn();
    const options = {
      ...baseOptions(),
      createMode: {
        isOpen: true,
        userType: 'sub_admin',
        companyId: '3',
        onRootCreated,
      },
    };
    const { result } = renderHook(() => useUserKnowledgeDirectories(options));

    await waitFor(() => expect(knowledgeApi.listKnowledgeDirectories).toHaveBeenCalledTimes(1));

    await act(async () => {
      await result.current.handleCreateModalRootDirectory(' New Root ');
    });

    expect(knowledgeApi.createKnowledgeDirectory).toHaveBeenCalledWith(
      { name: 'New Root', parent_id: null },
      { companyId: 3 }
    );
    expect(knowledgeApi.listKnowledgeDirectories).toHaveBeenLastCalledWith({ companyId: 3 });
    expect(onRootCreated).toHaveBeenCalledWith('node-created');
    expect(result.current.kbDirectoryCreateError).toBeNull();
  });

  it('surfaces validation errors before creating a root directory', async () => {
    const options = {
      ...baseOptions(),
      createMode: {
        isOpen: true,
        userType: 'sub_admin',
        companyId: '',
        onRootCreated: jest.fn(),
      },
    };
    const { result } = renderHook(() => useUserKnowledgeDirectories(options));

    await act(async () => {
      await result.current.handleCreateModalRootDirectory(' New Root ');
    });

    expect(knowledgeApi.createKnowledgeDirectory).not.toHaveBeenCalled();
    expect(result.current.kbDirectoryCreateError).toBe('company-required');
  });

  it('resets listing and root-creation state when no knowledge-directory mode remains active', async () => {
    const { result, rerender } = renderHook(
      (props) => useUserKnowledgeDirectories(props),
      {
        initialProps: {
          ...baseOptions(),
          createMode: {
            isOpen: true,
            userType: 'sub_admin',
            companyId: '2',
            onRootCreated: jest.fn(),
          },
        },
      }
    );

    await waitFor(() => expect(knowledgeApi.listKnowledgeDirectories).toHaveBeenCalledTimes(1));
    await act(async () => {
      await result.current.handleCreateModalRootDirectory('Root');
    });

    rerender(baseOptions());

    await waitFor(() => {
      expect(result.current.kbDirectoryNodes).toEqual([]);
    });
    expect(result.current.kbDirectoryCreateError).toBeNull();
    expect(result.current.kbDirectoryCreatingRoot).toBe(false);
  });

  it('marks the managed root invalid when the stored policy root is missing from the listing', async () => {
    knowledgeApi.listKnowledgeDirectories.mockResolvedValueOnce({ nodes: [] });

    const options = {
      ...baseOptions(),
      policyMode: {
        isOpen: true,
        userType: 'sub_admin',
        companyId: '1',
        selectedManagedKbRootNodeId: '',
        onRootCreated: jest.fn(),
      },
      policyUser: {
        managed_kb_root_node_id: 'node-missing',
        managed_kb_root_path: null,
      },
    };
    const { result } = renderHook(() => useUserKnowledgeDirectories(options));

    await waitFor(() => expect(knowledgeApi.listKnowledgeDirectories).toHaveBeenCalled());
    await waitFor(() => expect(result.current.managedKbRootInvalid).toBe(true));
  });
});
