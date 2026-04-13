export const buildUserKnowledgeDirectoryModes = ({ createManagement, policyManagement }) => ({
  createMode: {
    isOpen: createManagement.showCreateModal,
    userType: createManagement.newUser.user_type,
    companyId: createManagement.newUser.company_id,
    selectedManagedKbRootNodeId: createManagement.newUser.managed_kb_root_node_id,
    onRootCreated: (nodeId) =>
      createManagement.setNewUserField('managed_kb_root_node_id', nodeId),
  },
  policyMode: {
    isOpen: policyManagement.showPolicyModal,
    userType: policyManagement.policyForm.user_type,
    companyId: policyManagement.policyForm.company_id,
    selectedManagedKbRootNodeId: policyManagement.policyForm.managed_kb_root_node_id,
    onRootCreated: (nodeId) =>
      policyManagement.handleChangePolicyForm((prev) => ({
        ...prev,
        managed_kb_root_node_id: nodeId,
      })),
  },
});
