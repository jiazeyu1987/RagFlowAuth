import { act, renderHook } from '@testing-library/react';

import useSearchConfigsPanel from './useSearchConfigsPanel';
import useSearchConfigsPanelPage from './useSearchConfigsPanelPage';

jest.mock('./useSearchConfigsPanel', () => jest.fn());

const buildPanelState = (overrides = {}) => ({
  isAdmin: true,
  list: [],
  loading: false,
  error: '',
  filter: '',
  filteredList: [],
  selected: null,
  detailLoading: false,
  detailError: '',
  nameText: '',
  jsonText: '{}',
  saveStatus: '',
  busy: false,
  createOpen: false,
  createMode: 'blank',
  createName: '',
  createFromId: '',
  createJsonText: '{}',
  createError: '',
  setFilter: jest.fn(),
  setNameText: jest.fn(),
  setJsonText: jest.fn(),
  setCreateMode: jest.fn(),
  setCreateName: jest.fn(),
  setCreateFromId: jest.fn(),
  setCreateJsonText: jest.fn(),
  fetchList: jest.fn(),
  loadDetail: jest.fn(),
  save: jest.fn(),
  removeItem: jest.fn(),
  openCreate: jest.fn(),
  closeCreate: jest.fn(),
  syncCreateJsonFromCopy: jest.fn(),
  create: jest.fn(),
  resetDetailToSelected: jest.fn(),
  ...overrides,
});

describe('useSearchConfigsPanelPage', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useSearchConfigsPanel.mockReturnValue(buildPanelState());
  });

  it('resets copy source and json when switching back to blank create mode', () => {
    const state = buildPanelState();
    useSearchConfigsPanel.mockReturnValue(state);
    const { result } = renderHook(() => useSearchConfigsPanelPage());

    act(() => {
      result.current.handleCreateModeChange('blank');
    });

    expect(state.setCreateMode).toHaveBeenCalledWith('blank');
    expect(state.setCreateFromId).toHaveBeenCalledWith('');
    expect(state.setCreateJsonText).toHaveBeenCalledWith('{}');
  });

  it('updates copy source and syncs copied json through the feature hook', () => {
    const state = buildPanelState();
    useSearchConfigsPanel.mockReturnValue(state);
    const { result } = renderHook(() => useSearchConfigsPanelPage());

    act(() => {
      result.current.handleCreateSourceChange('cfg-2');
    });

    expect(state.setCreateFromId).toHaveBeenCalledWith('cfg-2');
    expect(state.syncCreateJsonFromCopy).toHaveBeenCalledWith('cfg-2');
  });
});
