import { useCallback, useEffect, useMemo, useState } from 'react';
import { auditApi } from './api';
import { usersApi } from '../users/api';
import { useAuth } from '../../hooks/useAuth';
import {
  LIST_LIMIT,
  collectKnowledgeBases,
  filterByKnowledgeBase,
  filterDocuments,
  sortDocuments,
} from './documentAuditHelpers';
import { OTHER_USER_TEXT } from './documentAuditView';

export default function useDocumentAuditData() {
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

      setUsers(userItems);
      setDocuments(sortDocuments(documentItems));
      setDeletions(deletionItems);
      setDownloads(downloadItems);
    } catch (requestError) {
      setError(requestError?.message || '\u52a0\u8f7d\u6587\u6863\u5ba1\u8ba1\u8bb0\u5f55\u5931\u8d25');
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
      return ref || OTHER_USER_TEXT;
    },
    [currentDisplayName, currentUserId, currentUsername, userMap]
  );

  const knowledgeBases = useMemo(
    () =>
      collectKnowledgeBases({
        documents,
        deletions,
        downloads,
      }),
    [deletions, documents, downloads]
  );

  const filteredDocuments = useMemo(
    () => filterDocuments({ documents, filterKb, filterStatus }),
    [documents, filterKb, filterStatus]
  );

  const filteredDeletions = useMemo(
    () => filterByKnowledgeBase({ items: deletions, filterKb }),
    [deletions, filterKb]
  );

  const filteredDownloads = useMemo(
    () => filterByKnowledgeBase({ items: downloads, filterKb }),
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
    knowledgeBases,
    filteredDocuments,
    filteredDeletions,
    filteredDownloads,
    setActiveTab,
    setFilterKb,
    setFilterStatus,
    resetFilters,
    resolveDisplayName,
  };
}
