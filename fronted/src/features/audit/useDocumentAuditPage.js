import { useCallback, useEffect, useMemo, useState } from 'react';
import { auditApi } from './api';
import { usersApi } from '../users/api';
import { useAuth } from '../../hooks/useAuth';

const LIST_LIMIT = 2000;

const createVersionsDialogState = () => ({
  open: false,
  loading: false,
  error: '',
  doc: null,
  items: [],
  currentDocId: '',
  logicalDocId: '',
});

const sortDocuments = (items) =>
  [...items].sort(
    (left, right) =>
      Number(right?.reviewed_at_ms || right?.uploaded_at_ms || 0) -
      Number(left?.reviewed_at_ms || left?.uploaded_at_ms || 0)
  );

export default function useDocumentAuditPage() {
  const { user } = useAuth();
  const [documents, setDocuments] = useState([]);
  const [deletions, setDeletions] = useState([]);
  const [downloads, setDownloads] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('documents');
  const [filterKb, setFilterKb] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [versionsDialog, setVersionsDialog] = useState(createVersionsDialogState);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [userItems, documentItems, deletionItems, downloadItems] = await Promise.all([
        usersApi.items({ limit: LIST_LIMIT }),
        auditApi.listDocuments({ limit: LIST_LIMIT }),
        auditApi.listDeletions({ limit: LIST_LIMIT }),
        auditApi.listDownloads({ limit: LIST_LIMIT }),
      ]);

      setUsers(Array.isArray(userItems) ? userItems : []);
      setDocuments(sortDocuments(Array.isArray(documentItems) ? documentItems : []));
      setDeletions(Array.isArray(deletionItems) ? deletionItems : []);
      setDownloads(Array.isArray(downloadItems) ? downloadItems : []);
    } catch (requestError) {
      setError(
        requestError?.message || '\u52a0\u8f7d\u6587\u6863\u5ba1\u8ba1\u8bb0\u5f55\u5931\u8d25'
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const userMap = useMemo(() => {
    const map = new Map();
    users.forEach((item) => {
      const displayName = item?.full_name || item?.username || '';
      if (item?.user_id && displayName) {
        map.set(item.user_id, displayName);
      }
      if (item?.username && displayName) {
        map.set(item.username, displayName);
      }
    });
    return map;
  }, [users]);

  const currentUserId = user?.user_id || '';
  const currentUsername = user?.username || '';
  const currentDisplayName = user?.full_name || currentUsername;

  const resolveDisplayName = useCallback(
    (ref, explicitName) => {
      if (ref && userMap.has(ref)) return userMap.get(ref);
      if (explicitName) return explicitName;
      if (ref && currentUsername && (ref === currentUserId || ref === currentUsername)) {
        return currentDisplayName;
      }
      return ref || '\u5176\u4ed6';
    },
    [currentDisplayName, currentUserId, currentUsername, userMap]
  );

  const closeVersionsDialog = useCallback(() => {
    setVersionsDialog(createVersionsDialogState());
  }, []);

  const openVersionsDialog = useCallback(async (doc) => {
    setVersionsDialog({
      ...createVersionsDialogState(),
      open: true,
      loading: true,
      doc,
    });

    try {
      const payload = await auditApi.listDocumentVersions(doc.doc_id);
      setVersionsDialog({
        open: true,
        loading: false,
        error: '',
        doc,
        items: Array.isArray(payload?.versions) ? payload.versions : [],
        currentDocId: payload?.currentDocId || '',
        logicalDocId: payload?.logicalDocId || '',
      });
    } catch (requestError) {
      setVersionsDialog((previous) => ({
        ...previous,
        loading: false,
        error: requestError?.message || '\u52a0\u8f7d\u7248\u672c\u5386\u53f2\u5931\u8d25',
      }));
    }
  }, []);

  const knowledgeBases = useMemo(() => {
    const values = new Set();
    documents.forEach((item) => {
      if (item?.kb_id) values.add(item.kb_id);
    });
    deletions.forEach((item) => {
      if (item?.kb_id) values.add(item.kb_id);
    });
    downloads.forEach((item) => {
      if (item?.kb_id) values.add(item.kb_id);
    });
    return Array.from(values);
  }, [deletions, documents, downloads]);

  const filteredDocuments = useMemo(
    () =>
      documents.filter((document) => {
        if (filterKb && document.kb_id !== filterKb) return false;
        if (filterStatus && document.status !== filterStatus) return false;
        return true;
      }),
    [documents, filterKb, filterStatus]
  );

  const filteredDeletions = useMemo(
    () =>
      deletions.filter((item) => {
        if (filterKb && item.kb_id !== filterKb) return false;
        return true;
      }),
    [deletions, filterKb]
  );

  const filteredDownloads = useMemo(
    () =>
      downloads.filter((item) => {
        if (filterKb && item.kb_id !== filterKb) return false;
        return true;
      }),
    [downloads, filterKb]
  );

  const resetFilters = useCallback(() => {
    setFilterKb('');
    setFilterStatus('');
  }, []);

  return {
    documents,
    deletions,
    downloads,
    loading,
    error,
    activeTab,
    filterKb,
    filterStatus,
    versionsDialog,
    knowledgeBases,
    filteredDocuments,
    filteredDeletions,
    filteredDownloads,
    setActiveTab,
    setFilterKb,
    setFilterStatus,
    resetFilters,
    resolveDisplayName,
    closeVersionsDialog,
    openVersionsDialog,
  };
}
