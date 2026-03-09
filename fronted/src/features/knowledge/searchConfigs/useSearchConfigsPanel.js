import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../../hooks/useAuth';
import { knowledgeApi } from '../api';
import { normalizeListResponse, parseJson, prettyJson } from './utils';

export default function useSearchConfigsPanel() {
  const { user } = useAuth();
  const isAdmin = (user?.role || '') === 'admin';

  const [list, setList] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [filter, setFilter] = useState('');

  const [selected, setSelected] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [nameText, setNameText] = useState('');
  const [jsonText, setJsonText] = useState('{}');
  const [saveStatus, setSaveStatus] = useState('');
  const [busy, setBusy] = useState(false);

  const [createOpen, setCreateOpen] = useState(false);
  const [createMode, setCreateMode] = useState('blank');
  const [createName, setCreateName] = useState('');
  const [createFromId, setCreateFromId] = useState('');
  const [createJsonText, setCreateJsonText] = useState('{}');
  const [createError, setCreateError] = useState('');

  const filteredList = useMemo(() => {
    const keyword = String(filter || '').trim().toLowerCase();
    if (!keyword) return list;
    return list.filter((item) => {
      const id = String(item?.id || '').toLowerCase();
      const name = String(item?.name || '').toLowerCase();
      return id.includes(keyword) || name.includes(keyword);
    });
  }, [filter, list]);

  const fetchList = useCallback(async () => {
    setError('');
    setLoading(true);
    try {
      const response = await knowledgeApi.listSearchConfigs();
      setList(normalizeListResponse(response));
    } catch (requestError) {
      setList([]);
      setError(requestError?.message || 'Failed to load configs');
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDetail = useCallback(async (configId) => {
    if (!configId) return;
    setDetailError('');
    setSaveStatus('');
    setDetailLoading(true);
    try {
      const config = await knowledgeApi.getSearchConfig(configId);
      if (!config || !config.id) throw new Error('config_not_found');
      setSelected(config);
      setNameText(String(config?.name || ''));
      setJsonText(prettyJson(config?.config || {}));
    } catch (requestError) {
      setSelected(null);
      setDetailError(requestError?.message || 'Failed to load config');
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchList();
  }, [fetchList]);

  useEffect(() => {
    if (!selected && list.length) loadDetail(list[0]?.id || '');
  }, [list, loadDetail, selected]);

  const save = useCallback(async () => {
    if (!selected?.id) return;
    setDetailError('');
    setSaveStatus('');

    const parsed = parseJson(jsonText);
    if (!parsed.ok) {
      setDetailError(parsed.error);
      return;
    }

    const name = String(nameText || selected.name || '').trim();
    if (!name) {
      setDetailError('Name is required');
      return;
    }

    setBusy(true);
    try {
      const updated = await knowledgeApi.updateSearchConfig(selected.id, {
        name,
        config: parsed.value,
      });
      if (!updated || !updated.id) throw new Error('update_success_without_payload');
      setSelected(updated);
      setNameText(String(updated?.name || name));
      setJsonText(prettyJson(updated?.config || parsed.value));
      setSaveStatus('Saved');
      await fetchList();
    } catch (requestError) {
      setDetailError(requestError?.message || 'Failed to save config');
    } finally {
      setBusy(false);
    }
  }, [fetchList, jsonText, nameText, selected]);

  const removeItem = useCallback(
    async (item) => {
      if (!item?.id) return;
      if (!window.confirm(`Delete search config: ${item.name || item.id}?`)) return;
      setBusy(true);
      try {
        await knowledgeApi.deleteSearchConfig(item.id);
        if (selected?.id === item.id) setSelected(null);
        await fetchList();
      } catch (requestError) {
        setError(requestError?.message || 'Failed to delete config');
      } finally {
        setBusy(false);
      }
    },
    [fetchList, selected?.id]
  );

  const openCreate = useCallback(() => {
    setCreateMode('blank');
    setCreateName('');
    setCreateFromId('');
    setCreateJsonText('{}');
    setCreateError('');
    setCreateOpen(true);
  }, []);

  const closeCreate = useCallback(() => {
    setCreateOpen(false);
  }, []);

  const syncCreateJsonFromCopy = useCallback(async (sourceId) => {
    if (!sourceId) return;
    setCreateError('');
    try {
      const source = await knowledgeApi.getSearchConfig(sourceId);
      if (!source || !source.id) throw new Error('source_config_not_found');
      setCreateJsonText(prettyJson(source?.config || {}));
    } catch (requestError) {
      setCreateJsonText('{}');
      setCreateError(requestError?.message || 'Failed to load source config');
    }
  }, []);

  const create = useCallback(async () => {
    if (!isAdmin) return;
    setCreateError('');

    const name = String(createName || '').trim();
    if (!name) {
      setCreateError('Name is required');
      return;
    }

    const parsed = parseJson(createJsonText);
    if (!parsed.ok) {
      setCreateError(parsed.error);
      return;
    }

    setBusy(true);
    try {
      const created = await knowledgeApi.createSearchConfig({
        name,
        config: parsed.value,
      });
      if (!created || !created.id) throw new Error('create_success_without_payload');
      setCreateOpen(false);
      await fetchList();
      await loadDetail(created.id);
    } catch (requestError) {
      setCreateError(requestError?.message || 'Failed to create config');
    } finally {
      setBusy(false);
    }
  }, [createJsonText, createName, fetchList, isAdmin, loadDetail]);

  const resetDetailToSelected = useCallback(() => {
    setNameText(String(selected?.name || ''));
    setJsonText(prettyJson(selected?.config || {}));
    setSaveStatus('');
    setDetailError('');
  }, [selected]);

  return {
    isAdmin,
    list,
    loading,
    error,
    filter,
    filteredList,
    selected,
    detailLoading,
    detailError,
    nameText,
    jsonText,
    saveStatus,
    busy,
    createOpen,
    createMode,
    createName,
    createFromId,
    createJsonText,
    createError,
    setFilter,
    setNameText,
    setJsonText,
    setCreateMode,
    setCreateName,
    setCreateFromId,
    setCreateJsonText,
    fetchList,
    loadDetail,
    save,
    removeItem,
    openCreate,
    closeCreate,
    syncCreateJsonFromCopy,
    create,
    resetDetailToSelected,
  };
}
