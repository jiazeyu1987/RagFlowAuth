import { useCallback, useEffect, useState } from 'react';
import { knowledgeApi } from '../knowledge/api';
import { loadPendingReviewDocuments, loadReviewDatasets } from './documentReviewUtils';

export function useDocumentReviewData(setError) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState('');
  const [assignedToMeOnly, setAssignedToMeOnly] = useState(true);
  const [loadingDatasets, setLoadingDatasets] = useState(true);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        setLoadingDatasets(true);
        const nextDatasets = await loadReviewDatasets(knowledgeApi);
        setDatasets(nextDatasets);

        if (nextDatasets.length === 0) {
          setError('您没有被分配任何知识库权限，请联系管理员');
        }
      } catch (_err) {
        setError('加载知识库列表失败');
        setDatasets([]);
        setDocuments([]);
        setLoading(false);
      } finally {
        setLoadingDatasets(false);
      }
    };

    fetchDatasets();
  }, [setError]);

  const refreshDocuments = useCallback(async () => {
    try {
      setLoading(true);
      const nextDocuments = await loadPendingReviewDocuments(knowledgeApi, selectedDataset, assignedToMeOnly);
      setDocuments(nextDocuments);
    } catch (err) {
      setError(err?.message || '加载待审文档失败');
      setDocuments([]);
    } finally {
      setLoading(false);
    }
  }, [assignedToMeOnly, selectedDataset, setError]);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  return {
    datasets,
    documents,
    loading,
    loadingDatasets,
    refreshDocuments,
    assignedToMeOnly,
    selectedDataset,
    setAssignedToMeOnly,
    setSelectedDataset,
  };
}
