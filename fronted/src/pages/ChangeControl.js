import React, { useCallback, useEffect, useState } from 'react';
import changeControlApi from '../features/changeControl/api';

const panelStyle = {
  background: '#ffffff',
  border: '1px solid #d7dde5',
  borderRadius: 8,
  padding: 16,
  boxShadow: '0 8px 20px rgba(15, 23, 42, 0.05)',
};

const inputStyle = {
  width: '100%',
  padding: 10,
  borderRadius: 6,
  border: '1px solid #c7d2de',
  boxSizing: 'border-box',
};

const buttonStyle = {
  padding: '8px 12px',
  borderRadius: 6,
  border: '1px solid #94a3b8',
  background: '#f8fafc',
  cursor: 'pointer',
};

const primaryButtonStyle = {
  ...buttonStyle,
  border: '1px solid #0f766e',
  background: '#0f766e',
  color: '#ffffff',
};

const initialCreateForm = {
  title: '',
  reason: '',
  owner_user_id: '',
  evaluator_user_id: '',
};

export default function ChangeControl({ onReturnToQualitySystem }) {
  const [loading, setLoading] = useState(true);
  const [working, setWorking] = useState(false);
  const [requests, setRequests] = useState([]);
  const [selectedRequestId, setSelectedRequestId] = useState('');
  const [createForm, setCreateForm] = useState(initialCreateForm);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const selectedRequest = requests.find((item) => item.request_id === selectedRequestId) || null;

  const loadRequests = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const items = await changeControlApi.listRequests({ limit: 50 });
      setRequests(items);
      if (items.length > 0 && !selectedRequestId) {
        setSelectedRequestId(items[0].request_id);
      }
    } catch (requestError) {
      setRequests([]);
      setError(requestError.message || 'Failed to load change requests');
    } finally {
      setLoading(false);
    }
  }, [selectedRequestId]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  const runAction = useCallback(
    async (runner, successMessage) => {
      setWorking(true);
      setError('');
      setSuccess('');
      try {
        await runner();
        setSuccess(successMessage);
        await loadRequests();
      } catch (actionError) {
        setError(actionError.message || 'Action failed');
      } finally {
        setWorking(false);
      }
    },
    [loadRequests]
  );

  return (
    <div data-testid="change-control-page" style={{ display: 'grid', gap: 16, padding: 20, background: '#f8fafc' }}>
      <div style={{ ...panelStyle, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2 style={{ margin: 0 }}>变更控制台账（WS04）</h2>
        <div style={{ display: 'flex', gap: 8 }}>
          {typeof onReturnToQualitySystem === 'function' ? (
            <button
              type="button"
              data-testid="change-control-return-quality-system"
              style={buttonStyle}
              onClick={onReturnToQualitySystem}
            >
              返回质量体系
            </button>
          ) : null}
          <button
            type="button"
            data-testid="change-control-dispatch-reminder"
            style={buttonStyle}
            onClick={() => runAction(() => changeControlApi.dispatchReminders(7), '已发送提醒')}
            disabled={working}
          >
            发送到期提醒
          </button>
        </div>
      </div>

      {error ? (
        <div data-testid="change-control-error" style={{ ...panelStyle, color: '#9f1239' }}>
          {error}
        </div>
      ) : null}
      {success ? (
        <div data-testid="change-control-success" style={{ ...panelStyle, color: '#166534' }}>
          {success}
        </div>
      ) : null}

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>新建变更申请</h3>
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <input
            data-testid="change-control-create-title"
            style={inputStyle}
            placeholder="标题"
            value={createForm.title}
            onChange={(event) => setCreateForm((prev) => ({ ...prev, title: event.target.value }))}
          />
          <input
            data-testid="change-control-create-reason"
            style={inputStyle}
            placeholder="变更原因"
            value={createForm.reason}
            onChange={(event) => setCreateForm((prev) => ({ ...prev, reason: event.target.value }))}
          />
          <input
            data-testid="change-control-create-owner-user-id"
            style={inputStyle}
            placeholder="责任人编号"
            value={createForm.owner_user_id}
            onChange={(event) => setCreateForm((prev) => ({ ...prev, owner_user_id: event.target.value }))}
          />
          <input
            data-testid="change-control-create-evaluator-user-id"
            style={inputStyle}
            placeholder="评估人编号"
            value={createForm.evaluator_user_id}
            onChange={(event) => setCreateForm((prev) => ({ ...prev, evaluator_user_id: event.target.value }))}
          />
        </div>
        <button
          type="button"
          data-testid="change-control-create-submit"
          style={{ ...primaryButtonStyle, marginTop: 10 }}
          disabled={working}
          onClick={() =>
            runAction(async () => {
              const created = await changeControlApi.createRequest({
                title: createForm.title.trim(),
                reason: createForm.reason.trim(),
                owner_user_id: createForm.owner_user_id.trim(),
                evaluator_user_id: createForm.evaluator_user_id.trim(),
                required_departments: ['qa'],
                affected_controlled_revisions: ['DOC-REV-001'],
              });
              setCreateForm(initialCreateForm);
              setSelectedRequestId(created.request_id);
            }, '变更申请已创建')
          }
        >
          创建
        </button>
      </section>

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>申请列表</h3>
        {loading ? <div data-testid="change-control-loading">加载中...</div> : null}
        {!loading && requests.length === 0 ? <div data-testid="change-control-empty">暂无申请</div> : null}
        <div style={{ display: 'grid', gap: 10 }}>
          {requests.map((item) => (
            <div
              key={item.request_id}
              data-testid={`change-control-row-${item.request_id}`}
              style={{
                border: selectedRequestId === item.request_id ? '1px solid #14b8a6' : '1px solid #d7dde5',
                borderRadius: 6,
                padding: 12,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                <strong>{item.title}</strong>
                <span>{item.status}</span>
              </div>
              <div style={{ marginTop: 6, color: '#475569' }}>{item.reason}</div>
              <button
                type="button"
                data-testid={`change-control-select-${item.request_id}`}
                style={{ ...buttonStyle, marginTop: 8 }}
                onClick={() => setSelectedRequestId(item.request_id)}
              >
                选择
              </button>
            </div>
          ))}
        </div>
      </section>

      {selectedRequest ? (
        <section style={panelStyle} data-testid="change-control-selected-request">
          <h3 style={{ marginTop: 0 }}>{selectedRequest.request_id}</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            <button
              type="button"
              data-testid="change-control-evaluate"
              style={buttonStyle}
              disabled={working}
              onClick={() =>
                runAction(
                  () => changeControlApi.evaluateRequest(selectedRequest.request_id, { evaluation_summary: '已完成风险评估' }),
                  '已完成评估'
                )
              }
            >
              评估
            </button>
            <button
              type="button"
              data-testid="change-control-add-plan-item"
              style={buttonStyle}
              disabled={working}
              onClick={() =>
                runAction(
                  () =>
                    changeControlApi.createPlanItem(selectedRequest.request_id, {
                      title: '执行受控变更',
                      assignee_user_id: selectedRequest.owner_user_id,
                      due_date: '2026-04-21',
                    }),
                  '已新增计划项'
                )
              }
            >
              新增计划项
            </button>
            <button
              type="button"
              data-testid="change-control-mark-planned"
              style={buttonStyle}
              disabled={working}
              onClick={() =>
                runAction(
                  () => changeControlApi.markPlanned(selectedRequest.request_id, { plan_summary: 'Plan confirmed' }),
                  'Request planned'
                )
              }
            >
              Mark planned
            </button>
            <button
              type="button"
              data-testid="change-control-start-execution"
              style={buttonStyle}
              disabled={working}
              onClick={() =>
                runAction(
                  () => changeControlApi.startExecution(selectedRequest.request_id),
                  'Execution started'
                )
              }
            >
              Start execution
            </button>
            <button
              type="button"
              data-testid="change-control-complete-execution"
              style={buttonStyle}
              disabled={working}
              onClick={() =>
                runAction(
                  () =>
                    changeControlApi.completeExecution(selectedRequest.request_id, {
                      execution_summary: 'Execution finished',
                    }),
                  'Execution completed'
                )
              }
            >
              Complete execution
            </button>
            <button
              type="button"
              data-testid="change-control-confirm-qa"
              style={buttonStyle}
              disabled={working}
              onClick={() =>
                runAction(
                  () =>
                    changeControlApi.confirmDepartment(selectedRequest.request_id, {
                      department_code: 'qa',
                      notes: 'qa ok',
                    }),
                  'Department confirmed'
                )
              }
            >
              Confirm QA
            </button>
            <button
              type="button"
              data-testid="change-control-close"
              style={primaryButtonStyle}
              disabled={working}
              onClick={() =>
                runAction(
                  () =>
                    changeControlApi.closeRequest(selectedRequest.request_id, {
                      close_summary: 'Close summary',
                      close_outcome: 'effective',
                      ledger_writeback_ref: 'LEDGER-1',
                      closed_controlled_revisions: ['DOC-REV-001'],
                    }),
                  'Request closed'
                )
              }
            >
              Close request
            </button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
