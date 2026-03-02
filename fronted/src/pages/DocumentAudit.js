import React, { useEffect, useMemo, useState } from 'react';
import authClient from '../api/authClient';
import { useAuth } from '../hooks/useAuth';

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

const baseHeaderCell = {
  padding: '12px 16px',
  textAlign: 'left',
  borderBottom: '1px solid #e5e7eb',
  fontSize: '0.85rem',
  fontWeight: '600',
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

const DocumentAudit = ({ embedded = false }) => {
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

  const userMap = useMemo(() => {
    const map = new Map();
    users.forEach((item) => {
      if (item?.user_id) map.set(item.user_id, item.username);
      if (item?.username) map.set(item.username, item.username);
    });
    return map;
  }, [users]);

  const currentUserId = user?.user_id || '';
  const currentUsername = user?.username || '';

  const resolveDisplayName = (ref, explicitName) => {
    if (explicitName) return explicitName;
    if (ref && userMap.has(ref)) return userMap.get(ref);
    if (ref && currentUsername && (ref === currentUserId || ref === currentUsername)) return currentUsername;
    return ref || '\u5176\u4ed6';
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
    <div style={{ display: 'flex', gap: '16px', alignItems: 'center', flexWrap: 'wrap' }}>
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
          }}
        >
          {'\u91cd\u7f6e'}
        </button>
      )}

      <span style={{ marginLeft: 'auto', fontSize: '0.9rem', color: '#6b7280' }}>
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
        {!embedded && <h2 style={{ margin: '0 0 16px 0' }}>{'\u6587\u6863\u5ba1\u6838\u8bb0\u5f55'}</h2>}

        <div style={{ marginBottom: '16px', borderBottom: '1px solid #e5e7eb' }}>
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
              marginRight: '8px',
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
              marginRight: '8px',
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
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: '900px' }}>
              <thead style={{ backgroundColor: '#f9fafb' }}>
                <tr>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u77e5\u8bc6\u5e93'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u6587\u4ef6\u540d'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u4e0a\u4f20\u8005'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u5ba1\u6838\u8005'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u72b6\u6001'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u4e0a\u4f20\u65f6\u95f4'}</th>
                  <th style={{ ...baseHeaderCell, color: '#374151' }}>{'\u5ba1\u6838\u65f6\u95f4'}</th>
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
    </div>
  );
};

export default DocumentAudit;
