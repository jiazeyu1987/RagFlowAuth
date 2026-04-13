import React from 'react';
import { useAuth } from '../../../hooks/useAuth';
import useTrainingAckPage from './useTrainingAckPage';

const cardStyle = {
  background: '#ffffff',
  border: '1px solid #dbe2ea',
  borderRadius: '14px',
  padding: '14px',
};

const buttonStyle = {
  border: '1px solid #cbd5e1',
  borderRadius: '8px',
  background: '#ffffff',
  color: '#0f172a',
  cursor: 'pointer',
  padding: '8px 10px',
};

const primaryButtonStyle = {
  ...buttonStyle,
  borderColor: '#0f766e',
  background: '#0f766e',
  color: '#ffffff',
};

const formatTime = (value) => {
  const ms = Number(value || 0);
  if (!Number.isFinite(ms) || ms <= 0) return '-';
  return new Date(ms).toLocaleString();
};

export default function TrainingAckWorkspace() {
  const { can } = useAuth();
  const canAssign = typeof can === 'function' ? can('training_ack', 'assign') : false;
  const canAcknowledge = true;
  const canReviewQuestions = typeof can === 'function' ? can('training_ack', 'review_questions') : false;
  const {
    loading,
    error,
    success,
    assignments,
    pendingAssignments,
    questionThreads,
    effectiveRevisions,
    selectedRevisionId,
    questionDrafts,
    resolutionDrafts,
    busyIds,
    generateBusy,
    setSelectedRevisionId,
    setQuestionDrafts,
    setResolutionDrafts,
    handleAcknowledge,
    handleResolveThread,
    handleGenerateAssignments,
  } = useTrainingAckPage({ canAssign, canAcknowledge, canReviewQuestions });

  if (loading) {
    return <div style={cardStyle}>正在加载培训任务...</div>;
  }

  return (
    <div style={{ display: 'grid', gap: '12px' }} data-testid="training-ack-workspace">
      {error ? <div style={{ ...cardStyle, color: '#991b1b', borderColor: '#fecaca' }}>{error}</div> : null}
      {success ? <div style={{ ...cardStyle, color: '#166534', borderColor: '#bbf7d0' }}>{success}</div> : null}

      {canAssign ? (
        <section style={cardStyle} data-testid="training-ack-generate-section">
          <h4 style={{ margin: 0 }}>生效文件生成培训任务</h4>
          <div style={{ marginTop: '10px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            <select
              value={selectedRevisionId}
              onChange={(event) => setSelectedRevisionId(event.target.value)}
              style={{ minWidth: '360px', padding: '8px' }}
            >
              {effectiveRevisions.map((item) => (
                <option key={item.controlled_revision_id} value={item.controlled_revision_id}>
                  {`${item.doc_code} v${item.revision_no} | ${item.title}`}
                </option>
              ))}
            </select>
            <button
              type="button"
              style={primaryButtonStyle}
              onClick={handleGenerateAssignments}
              disabled={generateBusy || !selectedRevisionId}
            >
              {generateBusy ? '生成中...' : '生成培训任务'}
            </button>
          </div>
        </section>
      ) : null}

      {canAcknowledge ? (
        <section style={cardStyle}>
          <h4 style={{ margin: 0 }}>待确认培训任务</h4>
          {pendingAssignments.length === 0 ? (
            <div style={{ marginTop: '10px', color: '#64748b' }}>暂无待确认项</div>
          ) : (
            <div style={{ marginTop: '10px', display: 'grid', gap: '10px' }}>
              {pendingAssignments.map((item) => {
                const busy = busyIds.includes(item.assignment_id);
                return (
                  <article key={item.assignment_id} style={{ border: '1px solid #e2e8f0', borderRadius: '10px', padding: '10px' }}>
                    <div style={{ fontWeight: 700 }}>{`${item.doc_code} v${item.revision_no}`}</div>
                    <div style={{ color: '#64748b', marginTop: '4px' }}>
                      最早确认时间: {formatTime(item.min_ack_at_ms)}
                    </div>
                    <textarea
                      value={questionDrafts[item.assignment_id] || ''}
                      onChange={(event) => setQuestionDrafts((previous) => ({ ...previous, [item.assignment_id]: event.target.value }))}
                      placeholder="如有疑问，请填写问题"
                      style={{ width: '100%', marginTop: '8px', minHeight: '68px' }}
                    />
                    <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }}>
                      <button type="button" style={primaryButtonStyle} disabled={busy} onClick={() => handleAcknowledge(item.assignment_id, 'acknowledged')}>
                        已知晓
                      </button>
                      <button type="button" style={buttonStyle} disabled={busy} onClick={() => handleAcknowledge(item.assignment_id, 'questioned')}>
                        有疑问
                      </button>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </section>
      ) : null}

      <section style={cardStyle}>
        <h4 style={{ margin: 0 }}>{canReviewQuestions ? '疑问闭环处理' : '我的疑问记录'}</h4>
        {questionThreads.length === 0 ? (
          <div style={{ marginTop: '10px', color: '#64748b' }}>暂无疑问记录</div>
        ) : (
          <div style={{ marginTop: '10px', display: 'grid', gap: '10px' }}>
            {questionThreads.map((thread) => {
              const busy = busyIds.includes(thread.thread_id);
              const open = String(thread.status || '') === 'open';
              return (
                <article key={thread.thread_id} style={{ border: '1px solid #e2e8f0', borderRadius: '10px', padding: '10px' }}>
                  <div><strong>问题:</strong> {thread.question_text}</div>
                  <div style={{ color: '#64748b', marginTop: '4px' }}>
                    提问时间: {formatTime(thread.raised_at_ms)} | 状态: {thread.status}
                  </div>
                  {canReviewQuestions && open ? (
                    <>
                      <textarea
                        value={resolutionDrafts[thread.thread_id] || ''}
                        onChange={(event) => setResolutionDrafts((previous) => ({ ...previous, [thread.thread_id]: event.target.value }))}
                        placeholder="填写处理结果"
                        style={{ width: '100%', marginTop: '8px', minHeight: '68px' }}
                      />
                      <div style={{ marginTop: '8px' }}>
                        <button
                          type="button"
                          style={primaryButtonStyle}
                          disabled={busy}
                          onClick={() => handleResolveThread(thread.thread_id)}
                        >
                          处理并闭环
                        </button>
                      </div>
                    </>
                  ) : (
                    <div style={{ marginTop: '6px' }}>
                      <strong>处理结果:</strong> {thread.resolution_text || '-'}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>

      <section style={cardStyle}>
        <h4 style={{ margin: 0 }}>全部培训任务</h4>
        <div style={{ marginTop: '10px', display: 'grid', gap: '8px' }}>
          {assignments.map((item) => (
            <div key={item.assignment_id} style={{ borderBottom: '1px solid #e2e8f0', paddingBottom: '6px' }}>
              {`${item.doc_code} v${item.revision_no} | ${item.status} | ${formatTime(item.acknowledged_at_ms || item.assigned_at_ms)}`}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
