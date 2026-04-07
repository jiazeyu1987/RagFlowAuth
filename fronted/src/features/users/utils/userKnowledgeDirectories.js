const normalizeOptionalNumber = (value) => {
  if (value == null || value === '') return null;
  const normalized = Number(value);
  return Number.isFinite(normalized) ? normalized : null;
};

export const isKnowledgeDirectoryModeActive = ({ isOpen, userType }) =>
  !!isOpen && String(userType || 'normal') === 'sub_admin';

export const shouldResetKnowledgeDirectoryState = ({
  showCreateModal,
  newUserType,
  showPolicyModal,
  policyUserType,
}) =>
  !isKnowledgeDirectoryModeActive({ isOpen: showCreateModal, userType: newUserType })
  && !isKnowledgeDirectoryModeActive({ isOpen: showPolicyModal, userType: policyUserType });

export const normalizeKnowledgeDirectoryCompanyId = (companyId) => normalizeOptionalNumber(companyId);

export const parseRootDirectoryCreationInput = ({ companyId, name }) => {
  const normalizedCompanyId = normalizeKnowledgeDirectoryCompanyId(companyId);
  if (normalizedCompanyId == null) {
    return { errorCode: 'company_required' };
  }

  const cleanName = String(name || '').trim();
  if (!cleanName) {
    return { errorCode: 'name_required' };
  }

  return {
    normalizedCompanyId,
    cleanName,
    errorCode: null,
  };
};

export const buildKnowledgeDirectoryQuery = ({ companyId, isAdminUser }) => {
  const normalizedCompanyId = normalizeKnowledgeDirectoryCompanyId(companyId);
  if (normalizedCompanyId == null) return null;
  return isAdminUser ? { companyId: normalizedCompanyId } : {};
};

export const buildEmptyKnowledgeDirectoryListingState = () => ({
  nodes: [],
  error: null,
});

export const buildKnowledgeDirectoryListingErrorState = (message) => ({
  nodes: [],
  error: message,
});

export const buildKnowledgeDirectoryListingSuccessState = (data) => ({
  nodes: Array.isArray(data?.nodes) ? data.nodes : [],
  error: null,
});

export const buildClearedKnowledgeDirectoryRootCreationState = ({ creatingRoot }) => ({
  creatingRoot: !!creatingRoot,
  error: null,
});

export const buildResetKnowledgeDirectoryRootCreationState = () => ({
  creatingRoot: false,
  error: null,
});

export const bindRootDirectoryCreateAction = (createRootDirectory, mode) =>
  async (name) =>
    createRootDirectory({
      companyId: mode.companyId,
      name,
      onCreated: mode.onRootCreated,
    });
