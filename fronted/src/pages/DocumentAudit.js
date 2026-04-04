import React, { useEffect, useMemo, useState } from 'react';
import authClient from '../api/authClient';
import { useAuth } from '../hooks/useAuth';

const MOBILE_BREAKPOINT = 768;

const STATUS_LABELS = {
  pending: '\u5f85\u5ba1\u6838',
  approved: '\u5df2\u901a\u8fc7',
  rejected: '\u5df2\u9a73\u56de',
};

const STATUS_STYLES = {
  pending: { backgroundColor: '#f59e0b' },
  approved: { backgroundColor: '#10b981' },
  rejected: { backgroundColor: '#ef4444' },
};

const EFFECTIVE_STATUS_LABELS = {
  approved: '当前生效',
  pending: '待审版本',
  rejected: '已驳回',
  superseded: '历史版本',
  archived: '归档版本',
};

const baseHeaderCell = {
  padding: '12px 16px',
  textAlign: 'left',
  borderBottom: '1px solid #e5e7eb',
  fontSize: '0.85rem',
  fontWeight: '600',
};

const manifestLabelStyle = {
  color: '#6b7280',
  fontSize: '0.8rem',
};

const manifestValueStyle = {
  color: '#111827',
  fontSize: '0.85rem',
  wordBreak: 'break-word',
};

const VERIFIED_TEXT = {
  yes: '\u901a\u8fc7',
  no: '\u5931\u8d25',
  unknown: '-',
};

const formatTime = (timestampMs) => {
  if (!timestampMs) return '-';
  return new Date(Number(timestampMs)).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const renderSignatureManifestation = (item) => {
  if (!item?.signature_id) {
    return <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>-</span>;
  }

  return (
    <div style={{ display: 'grid', gap: '6px' }}>
      <div>
        <div style={manifestLabelStyle}>{'\u7b7e\u540d\u4eba'}</div>
        <div style={manifestValueStyle}>{item.signed_by_full_name || item.signed_by_username || item.reviewed_by_name || item.reviewed_by || '-'}</div>
      </div>
      <div>
        <div style={manifestLabelStyle}>{'\u7b7e\u540d\u65f6\u95f4'}</div>
        <div style={manifestValueStyle}>{formatTime(item.signed_at_ms)}</div>
      </div>
      <div>
        <div style={manifestLabelStyle}>{'\u7b7e\u540d\u542b\u4e49'}</div>
        <div style={manifestValueStyle}>{item.signature_meaning || '-'}</div>
      </div>
      <div>
        <div style={manifestLabelStyle}>{'\u7b7e\u7f72\u539f\u56e0'}</div>
        <div style={manifestValueStyle}>{item.signature_reason || '-'}</div>
      </div>
      <div>
        <div style={manifestLabelStyle}>{'\u7b7e\u540d ID'}</div>
        <div style={{ ...manifestValueStyle, fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace" }}>
          {item.signature_id}
        </div>
      </div>
      <div>
        <div style={manifestLabelStyle}>{'\u9a8c\u7b7e\u7ed3\u679c'}</div>
        <div
          style={{
            ...manifestValueStyle,
            color: item.signature_verified === true ? '#166534' : item.signature_verified === false ? '#b91c1c' : manifestValueStyle.color,
            fontWeight: 600,
          }}
        >
          {item.signature_verified === true
            ? VERIFIED_TEXT.yes
            : item.signature_verified === false
              ? VERIFIED_TEXT.no
              : VERIFIED_TEXT.unknown}
        </div>
      </div>
    </div>
  );
};

const DocumentAudit = ({ embedded = false }) => {
  const { user } = useAuth();
  const [isMobile, setIsMobile] = useState(() => {
    if (typeof window === 'undefined') return false;
    return window.innerWidth <= MOBILE_BREAKPOINT;
  });
  const [documents, setDocuments] = useState([]);
  const [deletions, setDeletions] = useState([]);
  const [downloads, setDownloads] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('documents');
  const [filterKb, setFilterKb] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [versionsDialog, setVersionsDialog] = useState({
    open: false,
    loading: false,
    error: '',
    doc: null,
    items: [],
    currentDocId: '',
    logicalDocId: '',
  });

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError('');
      try {
        const [usersResp, docsResp, deletionsResp, downloadsResp] = await Promise.all([
          authClient.listUsers().catch(() => []),
          authClient.listDocuments({ limit: 2000 }).catch(() => ({ documents: [] })),
          authClient.listDeletions({ limit: 2000 }).catch(() => ({ deletions: [] })),
          authClient.listDownloads({ limit: 2000 }).catch(() => ({ downloads: [] })),
        ]);

        const docs = Array.isArray(docsResp?.documents) ? docsResp.documents : [];
        docs.sort((a, b) => Number(b.reviewed_at_ms || b.uploaded_at_ms || 0) - Number(a.reviewed_at_ms || a.uploaded_at_ms || 0));

        setUsers(Array.isArray(usersResp) ? usersResp : (usersResp?.users || []));
        setDocuments(docs);
        setDeletions(Array.isArray(deletionsResp?.deletions) ? deletionsResp.deletions : []);
        setDownloads(Array.isArray(downloadsResp?.downloads) ? downloadsResp.downloads : []);
      } catch (err) {
        setError(err?.message || 'load_failed');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const userMap = useMemo(() => {
    const map = new Map();
    users.forEach((item) => {
      const displayName = item?.full_name || item?.username || '';
      if (item?.user_id && displayName) map.set(item.user_id, displayName);
      if (item?.username && displayName) map.set(item.username, displayName);
    });
    return map;
  }, [users]);

  const currentUserId = user?.user_id || '';
  const currentUsername = user?.username || '';
  const currentDisplayName = user?.full_name || currentUsername;

  const resolveDisplayName = (ref, explicitName) => {
    if (ref && userMap.has(ref)) return userMap.get(ref);
    if (explicitName) return explicitName;
    if (ref && currentUsername && (ref === currentUserId || ref === currentUsername)) return currentDisplayName;
    return ref || '\u5176\u4ed6';
  };

  const closeVersionsDialog = () => {
    setVersionsDialog({
      open: false,
      loading: false,
      error: '',
      doc: null,
      items: [],
      currentDocId: '',
      logicalDocId: '',
    });
  };

  const openVersionsDialog = async (doc) => {
    setVersionsDialog({
      open: true,
      loading: true,
      error: '',
      doc,
      items: [],
      currentDocId: '',
      logicalDocId: '',
    });
    try {
      const payload = await authClient.listDocumentVersions(doc.doc_id);
      setVersionsDialog({
        open: true,
        loading: false,
        error: '',
        doc,
        items: Array.isArray(payload?.versions) ? payload.versions : [],
        currentDocId: payload?.current_doc_id || '',
        logicalDocId: payload?.logical_doc_id || '',
      });
    } catch (err) {
      setVersionsDialog((prev) => ({
        ...prev,
        loading: false,
        error: err?.message || '加载版本历史失败',
      }));
    }
  };

  const knowledgeBases = useMemo(() => {
    const kbSet = new Set();
    documents.forEach((item) => item?.kb_id && kbSet.add(item.kb_id));
    deletions.forEach((item) => item?.kb_id && kbSet.add(item.kb_id));
    downloads.forEach((item) => item?.kb_id && kbSet.add(item.kb_id));
    return Array.from(kbSet);
  }, [documents, deletions, downloads]);

  const filteredDocuments = useMemo(() => documents.filter((doc) => {
    if (filterKb && doc.kb_id !== filterKb) return false;
    if (filterStatus && doc.status !== filterStatus) return false;
    return true;
  }), [documents, filterKb, filterStatus]);

  const filteredDeletions = useMemo(() => deletions.filter((item) => {
    if (filterKb && item.kb_id !== filterKb) return false;
    return true;
  }), [deletions, filterKb]);

  const filteredDownloads = useMemo(() => downloads.filter((item) => {
    if (filterKb && item.kb_id !== filterKb) return false;
    return true;
  }), [downloads, filterKb]);

  const renderKbFilter = (withStatus = false) => (
    <div style={{ display: 'flex', gap: '16px', alignItems: isMobile ? 'stretch' : 'center', flexDirection: isMobile ? 'column' : 'row', flexWrap: 'wrap' }}>
      <div>
        <label style={{ marginRight: '8px', fontSize: '0.9rem', color: '#6b7280' }}>{'\u77e5\u8bc6\u5e93'}</label>
        <select
          value={filterKb}
          onChange={(e) => setFilterKb(e.target.value)}
          data-testid={withStatus ? 'audit-filter-kb' : undefined}
          style={{
            padding: '8px 12px',
            border: '1px solid #d1d5db',
            borderRadius: '4px',
            fontSize: '0.95rem',
            backgroundColor: 'white',
            cursor: 'pointer',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          <option value="">{'\u5168\u90e8\u77e5\u8bc6\u5e93'}</option>
          {knowledgeBases.map((kb) => (
            <option key={kb} value={kb}>{kb}</option>
          ))}
        </select>
      </div>

      {withStatus && (
        <div>
          <label style={{ marginRight: '8px', fontSize: '0.9rem', color: '#6b7280' }}>{'\u72b6\u6001'}</label>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            data-testid="audit-filter-status"
            style={{
              padding: '8px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              fontSize: '0.95rem',
              backgroundColor: 'white',
              cursor: 'pointer',
              width: isMobile ? '100%' : 'auto',
            }}
          >
            <option value="">{'\u5168\u90e8\u72b6\u6001'}</option>
            <option value="pending">{'\u5f85\u5ba1\u6838'}</option>
            <option value="approved">{'\u5df2\u901a\u8fc7'}</option>
            <option value="rejected">{'\u5df2\u9a73\u56de'}</option>
          </select>
        </div>
      )}

      {((withStatus && (filterKb || filterStatus)) || (!withStatus && filterKb)) && (
        <button
          onClick={() => {
            setFilterKb('');
            setFilterStatus('');
          }}
          data-testid={withStatus ? 'audit-filter-reset' : undefined}
          style={{
            padding: '8px 16px',
            backgroundColor: '#6b7280',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '0.9rem',
            width: isMobile ? '100%' : 'auto',
          }}
        >
          {'\u91cd\u7f6e'}
        </button>
      )}

      <span style={{ marginLeft: isMobile ? 0 : 'auto', fontSize: '0.9rem', color: '#6b7280', alignSelf: isMobile ? 'flex-start' : 'auto' }}>
        {withStatus ? `\u5171 ${filteredDocuments.length} \u6761\u8bb0\u5f55` : activeTab === 'deletions' ? `\u5171 ${filteredDeletions.length} \u6761\u8bb0\u5f55` : `\u5171 ${filteredDownloads.length} \u6761\u8bb0\u5f55`}
      </span>
    </div>
  );

  if (loading) {
    return <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>{'\u52a0\u8f7d\u4e2d...'}</div>;
  }

  return (
    <div data-testid="audit-page">
      <div style={{ marginBottom: '24px' }}>
        {!embedded && <h2 style={{ margin: '0 0 16px 0' }}>{'\u6587\u6863\u8bb0\u5f55'}</h2>}

        <div style={{ marginBottom: '16px', borderBottom: '1px solid #e5e7eb', display: 'flex', flexWrap: 'wrap', gap: isMobile ? '8px' : 0 }}>
          <button
            onClick={() => setActiveTab('documents')}
            data-testid="audit-tab-documents"
            style={{
              padding: '10px 20px',
              backgroundColor: activeTab === 'documents' ? '#3b82f6' : 'transparent',
              color: activeTab === 'documents' ? 'white' : '#6b7280',
              border: 'none',
              borderBottom: activeTab === 'documents' ? '2px solid #3b82f6' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '0.95rem',
              fontWeight: activeTab === 'documents' ? '600' : '400',
               marginRight: isMobile ? 0 : '8px',
            }}
          >
            {`\u6587\u6863\u5217\u8868 (${documents.length})`}
          </button>
          <button
            onClick={() => setActiveTab('deletions')}
            data-testid="audit-tab-deletions"
            style={{
              padding: '10px 20px',
              backgroundColor: activeTab === 'deletions' ? '#ef4444' : 'transparent',
              color: activeTab === 'deletions' ? 'white' : '#6b7280',
              border: 'none',
              borderBottom: activeTab === 'deletions' ? '2px solid #ef4444' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '0.95rem',
              fontWeight: activeTab === 'deletions' ? '600' : '400',
               marginRight: isMobile ? 0 : '8px',
            }}
          >
            {`\u5220\u9664\u8bb0\u5f55 (${deletions.length})`}
          </button>
          <button
            onClick={() => setActiveTab('downloads')}
            data-testid="audit-tab-downloads"
            style={{
              padding: '10px 20px',
              backgroundColor: activeTab === 'downloads' ? '#10b981' : 'transparent',
              color: activeTab === 'downloads' ? 'white' : '#6b7280',
              border: 'none',
              borderBottom: activeTab === 'downloads' ? '2px solid #10b981' : '2px solid transparent',
              cursor: 'pointer',
              fontSize: '0.95rem',
              fontWeight: activeTab === 'downloads' ? '600' : '400',
            }}
          >
            {`\u4e0b\u8f7d\u8bb0\u5f55 (${downloads.length})`}
          </button>
        </div>

        {activeTab === 'documents' ? renderKbFilter(true) : renderKbFilter(false)}
      </div>

      {error && (
        <div style={{ marginBottom: '16px', color: '#dc2626', fontSize: '0.95rem' }}>
          {error}
        </div>
      )}

      {activeTab === 'documents' ? (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1120px' }}>
              <thead style={{ backgroundColor: '#f9fafb' }}>
                <tr>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u77e5\u8bc6\u5e93'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u6587\u4ef6\u540d'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u4e0a\u4f20\u8005'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u5ba1\u6838\u8005'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u72b6\u6001'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u4e0a\u4f20\u65f6\u95f4'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u5ba1\u6838\u65f6\u95f4'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u7248\u672c\u5386\u53f2'}</th>
                </tr>
              </thead>
              <tbody>
                {filteredDocuments.map((doc, index) => (
                  <tr
                    key={doc.doc_id}
                    data-testid={`audit-doc-row-${doc.doc_id}`}
                    style={{
                      borderBottom: '1px solid #e5e7eb',
                      backgroundColor: index % 2 === 0 ? 'white' : '#f9fafb',
                    }}
                  >
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{doc.kb_id}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{doc.filename}</td>
                    <td style={{ display: 'none' }}>
                      <div style={{ fontWeight: 600 }}>v{doc.version_no || 1}</div>
                      <div style={{ color: '#6b7280', fontSize: '0.8rem', marginTop: 4 }}>
                        {doc.is_current === false ? '历史版本' : '当前记录'}
                      </div>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                      {resolveDisplayName(doc.uploaded_by, doc.uploaded_by_name)}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                      {doc.reviewed_by ? resolveDisplayName(doc.reviewed_by, doc.reviewed_by_name) : '\u5176\u4ed6'}
                    </td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        color: 'white',
                        fontSize: '0.85rem',
                        ...(STATUS_STYLES[doc.status] || { backgroundColor: '#6b7280' }),
                      }}>
                        {STATUS_LABELS[doc.status] || doc.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>{formatTime(doc.uploaded_at_ms)}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>{doc.reviewed_at_ms ? formatTime(doc.reviewed_at_ms) : '-'}</td>
                    <td style={{ display: 'none' }}>
                      {renderSignatureManifestation(doc)}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>
                      <button
                        type="button"
                        onClick={() => openVersionsDialog(doc)}
                        data-testid={`audit-doc-versions-${doc.doc_id}`}
                        style={{
                          padding: '6px 12px',
                          backgroundColor: '#eff6ff',
                          color: '#1d4ed8',
                          border: '1px solid #bfdbfe',
                          borderRadius: '6px',
                          cursor: 'pointer',
                        }}
                      >
                        查看版本历史
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredDocuments.length === 0 && (
            <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
              {filterKb || filterStatus ? '\u6ca1\u6709\u7b26\u5408\u6761\u4ef6\u7684\u8bb0\u5f55' : '\u6682\u65e0\u5ba1\u6838\u8bb0\u5f55'}
            </div>
          )}
        </>
      ) : activeTab === 'deletions' ? (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1000px' }}>
              <thead style={{ backgroundColor: '#fee2e2' }}>
                <tr>
                  <th style={{ ...baseHeaderCell, color: '#991b1b' }}>{'\u77e5\u8bc6\u5e93'}</th>
                  <th style={{ ...baseHeaderCell, color: '#991b1b' }}>{'\u6587\u4ef6\u540d'}</th>
                  <th style={{ ...baseHeaderCell, color: '#991b1b' }}>{'\u539f\u4e0a\u4f20\u8005'}</th>
                  <th style={{ ...baseHeaderCell, color: '#991b1b' }}>{'\u539f\u5ba1\u6838\u8005'}</th>
                  <th style={{ ...baseHeaderCell, color: '#991b1b' }}>{'\u5220\u9664\u8005'}</th>
                  <th style={{ ...baseHeaderCell, color: '#991b1b' }}>{'\u5220\u9664\u65f6\u95f4'}</th>
                </tr>
              </thead>
              <tbody>
                {filteredDeletions.map((del, index) => (
                  <tr
                    key={del.id}
                    data-testid={`audit-deletion-row-${del.id}`}
                    style={{
                      borderBottom: '1px solid #e5e7eb',
                      backgroundColor: index % 2 === 0 ? 'white' : '#fef2f2',
                    }}
                  >
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{del.kb_id}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{del.filename}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                      {resolveDisplayName(del.original_uploader, del.original_uploader_name)}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>
                      {del.original_reviewer ? resolveDisplayName(del.original_reviewer, del.original_reviewer_name) : '\u5176\u4ed6'}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#dc2626', fontWeight: '500' }}>
                      {resolveDisplayName(del.deleted_by, del.deleted_by_name)}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>{formatTime(del.deleted_at_ms)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredDeletions.length === 0 && (
            <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
              {filterKb ? '\u6ca1\u6709\u7b26\u5408\u6761\u4ef6\u7684\u5220\u9664\u8bb0\u5f55' : '\u6682\u65e0\u5220\u9664\u8bb0\u5f55'}
            </div>
          )}
        </>
      ) : (
        <>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1000px' }}>
              <thead style={{ backgroundColor: '#d1fae5' }}>
                <tr>
                  <th style={{ ...baseHeaderCell, color: '#065f46' }}>{'\u77e5\u8bc6\u5e93'}</th>
                  <th style={{ ...baseHeaderCell, color: '#065f46' }}>{'\u6587\u4ef6\u540d'}</th>
                  <th style={{ ...baseHeaderCell, color: '#065f46' }}>{'\u4e0b\u8f7d\u8005'}</th>
                  <th style={{ ...baseHeaderCell, color: '#065f46' }}>{'\u4e0b\u8f7d\u65f6\u95f4'}</th>
                  <th style={{ ...baseHeaderCell, color: '#065f46' }}>{'\u7c7b\u578b'}</th>
                </tr>
              </thead>
              <tbody>
                {filteredDownloads.map((down, index) => (
                  <tr
                    key={down.id}
                    data-testid={`audit-download-row-${down.id}`}
                    style={{
                      borderBottom: '1px solid #e5e7eb',
                      backgroundColor: index % 2 === 0 ? 'white' : '#f0fdf4',
                    }}
                  >
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{down.kb_id}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{down.filename}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#059669', fontWeight: '500' }}>
                      {resolveDisplayName(down.downloaded_by, down.downloaded_by_name)}
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.9rem', color: '#6b7280' }}>{formatTime(down.downloaded_at_ms)}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{
                        display: 'inline-block',
                        padding: '4px 8px',
                        borderRadius: '4px',
                        color: 'white',
                        fontSize: '0.85rem',
                        backgroundColor: down.is_batch ? '#059669' : '#10b981',
                      }}>
                        {down.is_batch ? '\u6279\u91cf\u4e0b\u8f7d' : '\u5355\u4e2a\u4e0b\u8f7d'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {filteredDownloads.length === 0 && (
            <div style={{ padding: '48px', textAlign: 'center', color: '#6b7280' }}>
              {filterKb ? '\u6ca1\u6709\u7b26\u5408\u6761\u4ef6\u7684\u4e0b\u8f7d\u8bb0\u5f55' : '\u6682\u65e0\u4e0b\u8f7d\u8bb0\u5f55'}
            </div>
          )}
        </>
      )}

      {versionsDialog.open ? (
        <div
          data-testid="audit-versions-modal"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(17, 24, 39, 0.42)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
            zIndex: 60,
          }}
          onClick={closeVersionsDialog}
        >
          <div
            style={{
              width: 'min(1100px, 100%)',
              maxHeight: '88vh',
              backgroundColor: 'white',
              borderRadius: '12px',
              border: '1px solid #e5e7eb',
              padding: '16px',
              overflow: 'auto',
            }}
            onClick={(event) => event.stopPropagation()}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'flex-start', marginBottom: 12 }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: '1.05rem' }}>
                  版本历史: {versionsDialog.doc?.filename || '-'}
                </div>
                <div style={{ color: '#6b7280', fontSize: '0.9rem', marginTop: 6 }}>
                  逻辑文档 ID: {versionsDialog.logicalDocId || '-'}
                </div>
              </div>
              <button
                type="button"
                onClick={closeVersionsDialog}
                style={{ border: 'none', background: 'transparent', cursor: 'pointer', fontSize: '1.2rem' }}
              >
                ×
              </button>
            </div>

            {versionsDialog.loading ? (
              <div style={{ padding: '24px 8px', color: '#6b7280' }}>加载版本历史中...</div>
            ) : versionsDialog.error ? (
              <div data-testid="audit-versions-error" style={{ padding: '12px 14px', background: '#fee2e2', color: '#991b1b', borderRadius: 8 }}>
                {versionsDialog.error}
              </div>
            ) : versionsDialog.items.length === 0 ? (
              <div style={{ padding: '24px 8px', color: '#6b7280' }}>暂无版本历史</div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '1260px' }}>
                  <thead style={{ backgroundColor: '#f9fafb' }}>
                    <tr>
                      <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u7248\u672c'}</th>
                      <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u6587\u4ef6\u540d'}</th>
                      <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u751f\u6548\u72b6\u6001'}</th>
                      <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u4e0a\u4f20\u8005'}</th>
                      <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u4e0a\u4f20\u65f6\u95f4'}</th>
                      <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u5f52\u6863\u65f6\u95f4'}</th>
                      <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u7535\u5b50\u7b7e\u540d'}</th>
                      <th style={{ ...baseHeaderCell, color: '#374151' }}>{'SHA256'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {versionsDialog.items.map((item, index) => {
                      const effectiveLabel = item.is_current
                        ? '当前生效'
                        : (EFFECTIVE_STATUS_LABELS[item.effective_status] || item.effective_status || '历史版本');
                      return (
                        <tr
                          key={item.doc_id}
                          data-testid={`audit-version-row-${item.doc_id}`}
                          style={{
                            borderBottom: '1px solid #e5e7eb',
                            backgroundColor: index % 2 === 0 ? 'white' : '#f9fafb',
                          }}
                        >
                          <td style={{ padding: '12px 16px', fontWeight: 600 }}>v{item.version_no || 1}</td>
                          <td style={{ padding: '12px 16px', fontSize: '0.9rem' }}>{item.filename}</td>
                          <td style={{ padding: '12px 16px' }}>
                            <span
                              style={{
                                display: 'inline-block',
                                padding: '4px 8px',
                                borderRadius: '999px',
                                backgroundColor: item.doc_id === versionsDialog.currentDocId ? '#dcfce7' : '#f3f4f6',
                                color: item.doc_id === versionsDialog.currentDocId ? '#166534' : '#374151',
                                fontSize: '0.85rem',
                              }}
                            >
                              {effectiveLabel}
                            </span>
                          </td>
                          <td style={{ padding: '12px 16px', color: '#6b7280' }}>
                            {resolveDisplayName(item.uploaded_by, item.uploaded_by_name)}
                          </td>
                          <td style={{ padding: '12px 16px', color: '#6b7280' }}>{formatTime(item.uploaded_at_ms)}</td>
                          <td style={{ padding: '12px 16px', color: '#6b7280' }}>{formatTime(item.archived_at_ms)}</td>
                          <td style={{ padding: '12px 16px', minWidth: '260px' }}>
                            {renderSignatureManifestation(item)}
                          </td>
                          <td style={{ padding: '12px 16px', fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace", fontSize: '0.82rem', wordBreak: 'break-all' }}>
                            {item.file_sha256 || '-'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default DocumentAudit;
