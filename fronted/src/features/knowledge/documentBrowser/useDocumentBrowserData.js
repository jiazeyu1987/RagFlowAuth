import { useCallback, useEffect, useState } from 'react';
import { knowledgeApi } from '../api';
import { documentBrowserApi } from './api';
import { TEXT } from './constants';

const EMPTY_TREE = { nodes: [], datasets: [] };

export default function useDocumentBrowserData({ can, accessibleKbs, user }) {
  const [datasets, setDatasets] = useState([]);
  const [directoryTree, setDirectoryTree] = useState(EMPTY_TREE);
  const [documents, setDocuments] = useState({});
  const [documentErrors, setDocumentErrors] = useState({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [canDeleteDocs, setCanDeleteDocs] = useState(false);
  const [canUploadDocs, setCanUploadDocs] = useState(false);

  useEffect(() => {
    setCanDeleteDocs(can('ragflow_documents', 'delete'));
    setCanUploadDocs(can('ragflow_documents', 'upload'));
  }, [can, user?.user_id]);

  useEffect(() => {
    setDocuments({});
    setDocumentErrors({});
    setDirectoryTree(EMPTY_TREE);
    setError(null);
  }, [user?.user_id]);

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        setLoading(true);
        const [datasetResponse, treeResponse] = await Promise.all([
          knowledgeApi.listRagflowDatasets(),
          knowledgeApi.listKnowledgeDirectories(),
        ]);
        if (cancelled) return;

        const nextDatasets = datasetResponse;
        setDatasets(nextDatasets);
        setDirectoryTree(treeResponse);
        setError(nextDatasets.length ? null : TEXT.noPermission);
      } catch (requestError) {
        if (cancelled) return;
        setError(requestError?.message || TEXT.loadKbFail);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();
    return () => {
      cancelled = true;
    };
  }, [accessibleKbs, user]);

  const fetchDocumentsForDataset = useCallback(async (datasetName) => {
    try {
      setDocumentErrors((previous) => {
        const next = { ...previous };
        delete next[datasetName];
        return next;
      });
      const items = await documentBrowserApi.listDocuments(datasetName);
      setDocuments((previous) => ({ ...previous, [datasetName]: items }));
    } catch (requestError) {
      setDocumentErrors((previous) => ({
        ...previous,
        [datasetName]: requestError?.message || TEXT.loadDocFail,
      }));
      setDocuments((previous) => ({ ...previous, [datasetName]: [] }));
    }
  }, []);

  return {
    datasets,
    setDatasets,
    directoryTree,
    setDirectoryTree,
    documents,
    setDocuments,
    documentErrors,
    setDocumentErrors,
    loading,
    error,
    setError,
    canDeleteDocs,
    canUploadDocs,
    fetchDocumentsForDataset,
  };
}
