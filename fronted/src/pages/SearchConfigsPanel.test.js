import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

import SearchConfigsPanel from './SearchConfigsPanel';
import useSearchConfigsPanelPage from '../features/knowledge/searchConfigs/useSearchConfigsPanelPage';

jest.mock('../features/knowledge/searchConfigs/useSearchConfigsPanelPage', () => jest.fn());

jest.mock(
  '../features/knowledge/searchConfigs/components/ConfigListPanel',
  () => function MockConfigListPanel(props) {
    return (
      <div data-testid="mock-config-list-panel">
        <button type="button" data-testid="mock-config-open-create" onClick={props.onOpenCreate}>
          open-create
        </button>
      </div>
    );
  }
);

jest.mock(
  '../features/knowledge/searchConfigs/components/ConfigDetailPanel',
  () => function MockConfigDetailPanel(props) {
    return (
      <div data-testid="mock-config-detail-panel">
        <button type="button" data-testid="mock-config-save" onClick={props.onSave}>
          save
        </button>
      </div>
    );
  }
);

jest.mock(
  '../features/knowledge/searchConfigs/components/CreateConfigDialog',
  () => function MockCreateConfigDialog(props) {
    if (!props.open) return null;
    return (
      <div data-testid="mock-create-config-dialog">
        <button type="button" data-testid="mock-config-mode-change" onClick={() => props.onChangeMode('blank')}>
          mode
        </button>
        <button type="button" data-testid="mock-config-from-change" onClick={() => props.onChangeFromId('cfg-2')}>
          from
        </button>
      </div>
    );
  }
);

const buildPageState = (overrides = {}) => ({
  isAdmin: true,
  isMobile: false,
  list: [{ id: 'cfg-1', name: 'Config A' }],
  loading: false,
  error: '',
  filter: '',
  filteredList: [{ id: 'cfg-1', name: 'Config A' }],
  selected: { id: 'cfg-1', name: 'Config A' },
  detailLoading: false,
  detailError: '',
  nameText: 'Config A',
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
  setCreateName: jest.fn(),
  setCreateJsonText: jest.fn(),
  fetchList: jest.fn(),
  loadDetail: jest.fn(),
  save: jest.fn(),
  removeItem: jest.fn(),
  openCreate: jest.fn(),
  closeCreate: jest.fn(),
  create: jest.fn(),
  resetDetailToSelected: jest.fn(),
  handleCreateModeChange: jest.fn(),
  handleCreateSourceChange: jest.fn(),
  ...overrides,
});

describe('SearchConfigsPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useSearchConfigsPanelPage.mockReturnValue(buildPageState());
  });

  it('renders the page shell and wires primary child actions through the page hook', async () => {
    const user = userEvent.setup();
    const openCreate = jest.fn();
    const save = jest.fn();

    useSearchConfigsPanelPage.mockReturnValue(
      buildPageState({
        openCreate,
        save,
      })
    );

    render(<SearchConfigsPanel />);

    expect(screen.getByTestId('search-configs-page')).toBeInTheDocument();
    expect(screen.getByTestId('mock-config-list-panel')).toBeInTheDocument();
    expect(screen.getByTestId('mock-config-detail-panel')).toBeInTheDocument();

    await user.click(screen.getByTestId('mock-config-open-create'));
    await user.click(screen.getByTestId('mock-config-save'));

    expect(openCreate).toHaveBeenCalledTimes(1);
    expect(save).toHaveBeenCalledTimes(1);
  });

  it('passes create dialog handlers from the page hook contract', async () => {
    const user = userEvent.setup();
    const handleCreateModeChange = jest.fn();
    const handleCreateSourceChange = jest.fn();

    useSearchConfigsPanelPage.mockReturnValue(
      buildPageState({
        createOpen: true,
        handleCreateModeChange,
        handleCreateSourceChange,
      })
    );

    render(<SearchConfigsPanel />);

    expect(screen.getByTestId('mock-create-config-dialog')).toBeInTheDocument();

    await user.click(screen.getByTestId('mock-config-mode-change'));
    await user.click(screen.getByTestId('mock-config-from-change'));

    expect(handleCreateModeChange).toHaveBeenCalledWith('blank');
    expect(handleCreateSourceChange).toHaveBeenCalledWith('cfg-2');
  });
});
