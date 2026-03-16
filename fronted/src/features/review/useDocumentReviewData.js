import { useCallback, useEffect, useState } from 'react';
import { knowledgeApi } from '../knowledge/api';
import { loadPendingReviewDocuments, loadReviewDatasets } from './documentReviewUtils';
import { normalizeDisplayError } from '../../shared/utils/displayError';

export function useDocumentReviewData(setError) {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [datasets, setDatasets] = useState([]);
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [loadingDatasets, setLoadingDatasets] = useState(true);

  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        setLoadingDatasets(true);
        const nextDatasets = await loadReviewDatasets(knowledgeApi);
        setDatasets(nextDatasets);

        if (nextDatasets.length > 0) {
          setSelectedDataset('');
        } else {
          setError('您没有被分配任何知识库权限，请联系管理员');
        }
      } catch (err) {
        setError('加载知识库列表失败');
        setDatasets([]);
      } finally {
        setLoadingDatasets(false);
      }
    };

    fetchDatasets();
  }, [setError]);

  const refreshDocuments = useCallback(async () => {
    if (selectedDataset === null) return;

    try {
      setLoading(true);
      const nextDocuments = await loadPendingReviewDocuments(knowledgeApi, selectedDataset);
      setDocuments(nextDocuments);
    } catch (err) {
      setError(normalizeDisplayError(err?.message ?? err, '?????????'));
    } finally {
      setLoading(false);
    }
  }, [selectedDataset, setError]);

  useEffect(() => {
    refreshDocuments();
  }, [refreshDocuments]);

  return {
    datasets,
    documents,
    loading,
    loadingDatasets,
    refreshDocuments,
    selectedDataset,
    setSelectedDataset,
  };
}
