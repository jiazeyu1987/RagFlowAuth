import { act, renderHook, waitFor } from '@testing-library/react';
import useSearchConfigsPanel from './useSearchConfigsPanel';
import { knowledgeApi } from '../api';

jest.mock('../../../hooks/useAuth', () => ({
  useAuth: jest.fn(),
}));

jest.mock('../api', () => ({
  knowledgeApi: {
    listSearchConfigs: jest.fn(),
    getSearchConfig: jest.fn(),
    updateSearchConfig: jest.fn(),
    deleteSearchConfig: jest.fn(),
    createSearchConfig: jest.fn(),
  },
}));

const { useAuth } = jest.requireMock('../../../hooks/useAuth');

describe('useSearchConfigsPanel', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuth.mockReturnValue({
      user: { role: 'admin' },
    });
    knowledgeApi.listSearchConfigs.mockResolvedValue([{ id: 'cfg-1', name: 'Config A' }]);
    knowledgeApi.getSearchConfig.mockResolvedValue({
      id: 'cfg-1',
      name: 'Config A',
      config: { enabled: true },
    });
    knowledgeApi.updateSearchConfig.mockResolvedValue({
      id: 'cfg-1',
      name: 'Config B',
      config: { enabled: false },
    });
    knowledgeApi.createSearchConfig.mockResolvedValue({
      id: 'cfg-2',
      name: 'Config C',
      config: { mode: 'copy' },
    });
  });

  it('loads the stable config list and auto-loads the first config detail', async () => {
    const { result } = renderHook(() => useSearchConfigsPanel());

    await waitFor(() => {
      expect(knowledgeApi.listSearchConfigs).toHaveBeenCalled();
      expect(knowledgeApi.getSearchConfig).toHaveBeenCalledWith('cfg-1');
      expect(result.current.list).toEqual([{ id: 'cfg-1', name: 'Config A' }]);
      expect(result.current.selected).toEqual(
        expect.objectContaining({
          id: 'cfg-1',
          name: 'Config A',
        })
      );
    });
  });

  it('saves edited configs through the feature API and refreshes the list', async () => {
    const { result } = renderHook(() => useSearchConfigsPanel());

    await waitFor(() => {
      expect(result.current.selected?.id).toBe('cfg-1');
    });

    act(() => {
      result.current.setNameText('Config B');
      result.current.setJsonText('{"enabled": false}');
    });

    await act(async () => {
      await result.current.save();
    });

    expect(knowledgeApi.updateSearchConfig).toHaveBeenCalledWith('cfg-1', {
      name: 'Config B',
      config: { enabled: false },
    });
    expect(result.current.selected).toEqual(
      expect.objectContaining({
        id: 'cfg-1',
        name: 'Config B',
      })
    );
  });
});
