import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  OVERVIEW_TAB,
  SEARCH_RESULT_LIMIT,
  collectBranchKeys,
  countNodeType,
  flattenSearchEntries,
  matchesSearchTerm,
  toNodeKey,
} from './helpers';

export default function useOrgDirectorySearchState({
  tree,
  companies,
  departments,
  isMobile,
  nodeRefs,
  setActiveTab,
}) {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSearchKey, setSelectedSearchKey] = useState(null);
  const [selectedPersonNodeKey, setSelectedPersonNodeKey] = useState(null);
  const [highlightedNodeKey, setHighlightedNodeKey] = useState(null);
  const [expandedKeys, setExpandedKeys] = useState(new Set());

  const personColumnCount = isMobile ? 2 : 4;
  const personCount = useMemo(() => countNodeType(tree, 'person'), [tree]);
  const hasOrgData = tree.length > 0 || companies.length > 0 || departments.length > 0;
  const isMissingPersonNodes = hasOrgData && personCount === 0;
  const searchEntries = useMemo(() => flattenSearchEntries(tree), [tree]);
  const selectedPersonEntry = useMemo(
    () =>
      searchEntries.find(
        (entry) => entry.key === selectedPersonNodeKey && entry.nodeType === 'person'
      ) || null,
    [searchEntries, selectedPersonNodeKey]
  );
  const trimmedSearchTerm = searchTerm.trim().toLowerCase();
  const totalSearchMatches = useMemo(() => {
    if (!trimmedSearchTerm) return 0;
    return searchEntries.filter((entry) => matchesSearchTerm(entry, trimmedSearchTerm)).length;
  }, [searchEntries, trimmedSearchTerm]);
  const searchResults = useMemo(() => {
    if (!trimmedSearchTerm) return [];
    return searchEntries
      .filter((entry) => matchesSearchTerm(entry, trimmedSearchTerm))
      .slice(0, SEARCH_RESULT_LIMIT);
  }, [searchEntries, trimmedSearchTerm]);

  useEffect(() => {
    setExpandedKeys(new Set());
  }, [tree]);

  useEffect(() => {
    if (!highlightedNodeKey) return undefined;
    const target = nodeRefs.current.get(highlightedNodeKey);
    if (target && typeof target.scrollIntoView === 'function') {
      target.scrollIntoView({ block: 'center', behavior: 'smooth' });
    }
    const timerId = window.setTimeout(() => setHighlightedNodeKey(null), 2200);
    return () => window.clearTimeout(timerId);
  }, [highlightedNodeKey, nodeRefs]);

  const registerNodeRef = useCallback(
    (key, element) => {
      if (element) {
        nodeRefs.current.set(key, element);
      } else {
        nodeRefs.current.delete(key);
      }
    },
    [nodeRefs]
  );

  const resetTreeView = useCallback(() => {
    setExpandedKeys(new Set());
    setSelectedSearchKey(null);
    setHighlightedNodeKey(null);
  }, []);

  const resetAfterRebuild = useCallback(() => {
    setSearchTerm('');
    setSelectedSearchKey(null);
    setSelectedPersonNodeKey(null);
    setHighlightedNodeKey(null);
    setExpandedKeys(new Set());
  }, []);

  const handleSearchInputChange = useCallback(
    (event) => {
      setSearchTerm(event.target.value);
      resetTreeView();
    },
    [resetTreeView]
  );

  const handleClearSearch = useCallback(() => {
    setSearchTerm('');
    resetTreeView();
  }, [resetTreeView]);

  const handleSelectSearchResult = useCallback(
    (entry) => {
      if (!entry) return;
      setSelectedSearchKey(entry.key);

      if (entry.nodeType === 'company') {
        setExpandedKeys(new Set(collectBranchKeys([entry.node])));
        setSelectedPersonNodeKey(null);
      } else if (entry.nodeType === 'department') {
        setExpandedKeys(new Set(entry.branchPathKeys));
        setSelectedPersonNodeKey(null);
      } else {
        setExpandedKeys(new Set(entry.branchPathKeys));
        setSelectedPersonNodeKey(entry.key);
        setActiveTab(OVERVIEW_TAB);
      }

      setHighlightedNodeKey(entry.key);
    },
    [setActiveTab]
  );

  const handleSelectPerson = useCallback(
    (personNode) => {
      if (!personNode || personNode.node_type !== 'person') return;
      const nodeKey = toNodeKey(personNode);
      setSelectedPersonNodeKey(nodeKey);
      setSelectedSearchKey(null);
      setHighlightedNodeKey(nodeKey);
      setActiveTab(OVERVIEW_TAB);
    },
    [setActiveTab]
  );

  const handleToggleBranch = useCallback((nodeKey) => {
    setExpandedKeys((previous) => {
      const next = new Set(previous);
      if (next.has(nodeKey)) next.delete(nodeKey);
      else next.add(nodeKey);
      return next;
    });
  }, []);

  return {
    searchTerm,
    selectedSearchKey,
    selectedPersonNodeKey,
    selectedPersonEntry,
    highlightedNodeKey,
    expandedKeys,
    personColumnCount,
    personCount,
    isMissingPersonNodes,
    trimmedSearchTerm,
    totalSearchMatches,
    searchResults,
    registerNodeRef,
    resetAfterRebuild,
    handleSearchInputChange,
    handleClearSearch,
    handleSelectSearchResult,
    handleSelectPerson,
    handleToggleBranch,
  };
}
