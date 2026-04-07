import {
  bindRootDirectoryCreateAction,
  buildClearedKnowledgeDirectoryRootCreationState,
  buildEmptyKnowledgeDirectoryListingState,
  buildKnowledgeDirectoryListingErrorState,
  buildKnowledgeDirectoryListingSuccessState,
  buildKnowledgeDirectoryQuery,
  buildResetKnowledgeDirectoryRootCreationState,
  isKnowledgeDirectoryModeActive,
  normalizeKnowledgeDirectoryCompanyId,
  parseRootDirectoryCreationInput,
  shouldResetKnowledgeDirectoryState,
} from './userKnowledgeDirectories';

describe('userKnowledgeDirectories', () => {
  it('detects when a sub admin knowledge-directory mode is active', () => {
    expect(isKnowledgeDirectoryModeActive({ isOpen: true, userType: 'sub_admin' })).toBe(true);
    expect(isKnowledgeDirectoryModeActive({ isOpen: false, userType: 'sub_admin' })).toBe(false);
    expect(isKnowledgeDirectoryModeActive({ isOpen: true, userType: 'normal' })).toBe(false);
  });

  it('knows when managed knowledge-directory state should reset', () => {
    expect(
      shouldResetKnowledgeDirectoryState({
        showCreateModal: false,
        newUserType: 'sub_admin',
        showPolicyModal: false,
        policyUserType: 'normal',
      })
    ).toBe(true);

    expect(
      shouldResetKnowledgeDirectoryState({
        showCreateModal: true,
        newUserType: 'sub_admin',
        showPolicyModal: false,
        policyUserType: 'normal',
      })
    ).toBe(false);
  });

  it('normalizes company ids used by knowledge-directory requests', () => {
    expect(normalizeKnowledgeDirectoryCompanyId('12')).toBe(12);
    expect(normalizeKnowledgeDirectoryCompanyId('')).toBeNull();
  });

  it('parses root directory creation input and fails fast on missing fields', () => {
    expect(parseRootDirectoryCreationInput({ companyId: '', name: 'Root' })).toEqual({
      errorCode: 'company_required',
    });

    expect(parseRootDirectoryCreationInput({ companyId: '12', name: '   ' })).toEqual({
      errorCode: 'name_required',
    });

    expect(parseRootDirectoryCreationInput({ companyId: '12', name: ' Root A ' })).toEqual({
      normalizedCompanyId: 12,
      cleanName: 'Root A',
      errorCode: null,
    });
  });

  it('builds directory list query params based on admin scope', () => {
    expect(buildKnowledgeDirectoryQuery({ companyId: '12', isAdminUser: true })).toEqual({ companyId: 12 });
    expect(buildKnowledgeDirectoryQuery({ companyId: '12', isAdminUser: false })).toEqual({});
    expect(buildKnowledgeDirectoryQuery({ companyId: '', isAdminUser: true })).toBeNull();
  });

  it('builds normalized listing states for empty, error, and success cases', () => {
    expect(buildEmptyKnowledgeDirectoryListingState()).toEqual({
      nodes: [],
      error: null,
    });

    expect(buildKnowledgeDirectoryListingErrorState('load_failed')).toEqual({
      nodes: [],
      error: 'load_failed',
    });

    expect(buildKnowledgeDirectoryListingSuccessState({ nodes: [{ id: 'node-1' }] })).toEqual({
      nodes: [{ id: 'node-1' }],
      error: null,
    });
  });

  it('builds root creation states for clear and reset cases', () => {
    expect(
      buildClearedKnowledgeDirectoryRootCreationState({ creatingRoot: true })
    ).toEqual({
      creatingRoot: true,
      error: null,
    });

    expect(buildResetKnowledgeDirectoryRootCreationState()).toEqual({
      creatingRoot: false,
      error: null,
    });
  });

  it('binds root creation actions from a mode descriptor', async () => {
    const createRootDirectory = jest.fn().mockResolvedValue('node-1');
    const onRootCreated = jest.fn();
    const action = bindRootDirectoryCreateAction(createRootDirectory, {
      companyId: '12',
      onRootCreated,
    });

    await expect(action('Root A')).resolves.toBe('node-1');
    expect(createRootDirectory).toHaveBeenCalledWith({
      companyId: '12',
      name: 'Root A',
      onCreated: onRootCreated,
    });
  });
});
