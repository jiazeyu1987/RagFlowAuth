import { useEffect, useMemo, useState } from 'react';

import { knowledgeApi } from '../api';
import { mapUserFacingErrorMessage } from '../../../shared/errors/userFacingErrorMessages';

const normalizeKbRef = (value) => String(value || '').trim();

const getDatasetValue = (dataset) => dataset?.name || dataset?.id || '';

const getDatasetLabel = (dataset) => {
  const name = String(dataset?.name || dataset?.id || '').trim();
  const nodePath = String(dataset?.node_path || '').trim();
  if (!name) return '';
  if (!nodePath || nodePath === '/') return name;
  return `${nodePath}/${name}`;
};

const mergeDatasetDirectoryInfo = (datasets, directoryDatasets) => {
  const nodePathById = new Map();
  const nodePathByName = new Map();

  directoryDatasets.forEach((dataset) => {
    const nodePath = String(dataset?.node_path || '').trim();
    const id = normalizeKbRef(dataset?.id);
    const name = normalizeKbRef(dataset?.name);

    if (id) nodePathById.set(id, nodePath);
    if (name) nodePathByName.set(name, nodePath);
  });

  return datasets.map((dataset) => {
    const id = normalizeKbRef(dataset?.id);
    const name = normalizeKbRef(dataset?.name);
    const nodePath = nodePathById.get(id) || nodePathByName.get(name) || dataset?.node_path || '/';

    return {
      ...dataset,
      node_path: nodePath,
    };
  });
};

const filterDatasetsByVisibility = (allDatasets, visibleKbRefs) => {
  const list = Array.isArray(allDatasets) ? allDatasets : [];
  if (visibleKbRefs.size === 0) return [];

  return list.filter((dataset) => {
    const id = normalizeKbRef(dataset?.id);
    const name = normalizeKbRef(dataset?.name);
    return (id && visibleKbRefs.has(id)) || (name && visibleKbRefs.has(name));
  });
};

export default function useKnowledgeUploadDatasets({ accessibleKbs, authLoading, setError }) {
  const [kbId, setKbId] = useState('');
  const [kbSearchKeyword, setKbSearchKeyword] = useState('');
  const [datasets, setDatasets] = useState([]);
  const [loadingDatasets, setLoadingDatasets] = useState(true);

  const datasetOptions = useMemo(
    () =>
      (datasets || [])
        .map((dataset) => ({
          key: dataset?.id || getDatasetValue(dataset),
          value: getDatasetValue(dataset),
          label: getDatasetLabel(dataset),
        }))
        .filter((option) => option.value && option.label)
        .sort((left, right) =>
          String(left.label || '').localeCompare(String(right.label || ''), 'zh-Hans-CN')
        ),
    [datasets]
  );

  const filteredDatasetOptions = useMemo(() => {
    const keyword = String(kbSearchKeyword || '').trim().toLowerCase();
    if (!keyword) return datasetOptions;

    return datasetOptions.filter((option) => {
      const label = String(option?.label || '').toLowerCase();
      const value = String(option?.value || '').toLowerCase();
      return label.includes(keyword) || value.includes(keyword);
    });
  }, [datasetOptions, kbSearchKeyword]);

  useEffect(() => {
    if (loadingDatasets) return;
    if (filteredDatasetOptions.length === 0) return;
    if (filteredDatasetOptions.some((option) => option.value === kbId)) return;
    setKbId(filteredDatasetOptions[0].value);
  }, [filteredDatasetOptions, kbId, loadingDatasets]);

  useEffect(() => {
    let active = true;

    const fetchDatasets = async () => {
      if (authLoading) return;

      try {
        setLoadingDatasets(true);

        const [datasetItems, directoryTree] = await Promise.all([
          knowledgeApi.listRagflowDatasets(),
          knowledgeApi.listKnowledgeDirectories(),
        ]);

        if (!active) return;

        const allDatasets = mergeDatasetDirectoryInfo(datasetItems, directoryTree.datasets);
        const visibleKbRefs = new Set(
          (Array.isArray(accessibleKbs) ? accessibleKbs : [])
            .map(normalizeKbRef)
            .filter(Boolean)
        );
        const visibleDatasets = filterDatasetsByVisibility(allDatasets, visibleKbRefs);
        const datasetValues = new Set(
          visibleDatasets.map((dataset) => getDatasetValue(dataset)).filter(Boolean)
        );

        setDatasets(visibleDatasets);

        if (visibleDatasets.length > 0) {
          const firstVisibleKb = getDatasetValue(visibleDatasets[0]);
          setKbId((current) => (current && datasetValues.has(current) ? current : firstVisibleKb));
          setError(null);
        } else {
          setKbId('');
          setError('您没有被分配任何知识库权限，请联系管理员');
        }
      } catch (requestError) {
        if (!active) return;
        setDatasets([]);
        setKbId('');
        setError(mapUserFacingErrorMessage(requestError?.message, '无法加载知识库列表，请检查网络连接'));
      } finally {
        if (active) {
          setLoadingDatasets(false);
        }
      }
    };

    fetchDatasets();

    return () => {
      active = false;
    };
  }, [accessibleKbs, authLoading, setError]);

  return {
    kbId,
    setKbId,
    kbSearchKeyword,
    setKbSearchKeyword,
    datasets,
    loadingDatasets,
    datasetOptions,
    filteredDatasetOptions,
  };
}
