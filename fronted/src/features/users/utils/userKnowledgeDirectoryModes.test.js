import { buildUserKnowledgeDirectoryModes } from './userKnowledgeDirectoryModes';

describe('buildUserKnowledgeDirectoryModes', () => {
  it('maps create-management state and forwards created roots back to the draft', () => {
    const setNewUserField = jest.fn();
    const modes = buildUserKnowledgeDirectoryModes({
      createManagement: {
        showCreateModal: true,
        newUser: {
          user_type: 'sub_admin',
          company_id: '1',
        },
        setNewUserField,
      },
      policyManagement: {
        showPolicyModal: false,
        policyForm: {
          user_type: 'viewer',
          company_id: '',
          managed_kb_root_node_id: '',
        },
        handleChangePolicyForm: jest.fn(),
      },
    });

    expect(modes.createMode).toEqual(
      expect.objectContaining({
        isOpen: true,
        userType: 'sub_admin',
        companyId: '1',
      })
    );

    modes.createMode.onRootCreated('node-created');
    expect(setNewUserField).toHaveBeenCalledWith('managed_kb_root_node_id', 'node-created');
  });

  it('maps policy-management state and rewrites the selected managed root', () => {
    const handleChangePolicyForm = jest.fn();
    const modes = buildUserKnowledgeDirectoryModes({
      createManagement: {
        showCreateModal: false,
        newUser: {
          user_type: 'viewer',
          company_id: '',
        },
        setNewUserField: jest.fn(),
      },
      policyManagement: {
        showPolicyModal: true,
        policyForm: {
          user_type: 'sub_admin',
          company_id: '2',
          managed_kb_root_node_id: 'node-old',
        },
        handleChangePolicyForm,
      },
    });

    expect(modes.policyMode).toEqual(
      expect.objectContaining({
        isOpen: true,
        userType: 'sub_admin',
        companyId: '2',
        selectedManagedKbRootNodeId: 'node-old',
      })
    );

    modes.policyMode.onRootCreated('node-new');

    const updater = handleChangePolicyForm.mock.calls[0][0];
    expect(
      updater({
        managed_kb_root_node_id: 'node-old',
        untouched: true,
      })
    ).toEqual({
      managed_kb_root_node_id: 'node-new',
      untouched: true,
    });
  });
});
