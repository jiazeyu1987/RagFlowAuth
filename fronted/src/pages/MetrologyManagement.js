import React, { useCallback, useEffect, useMemo, useState } from 'react';
import metrologyApi from '../features/metrology/api';

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

const initialForm = {
  equipment_id: '',
  responsible_user_id: '',
  planned_due_date: '',
  summary: '',
};

const STATUS_ACTIONS = {
  planned: ['record'],
  recorded: ['confirm'],
  confirmed: ['approve'],
};

export default function MetrologyManagement() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [records, setRecords] = useState([]);
  const [createForm, setCreateForm] = useState(initialForm);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadRecords = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const next = await metrologyApi.listRecords({ limit: 100 });
      setRecords(next);
    } catch (err) {
      setError(err.message || '加载计量记录失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRecords();
  }, [loadRecords]);

  const createPayload = useMemo(
    () => ({
      equipment_id: createForm.equipment_id.trim(),
      responsible_user_id: createForm.responsible_user_id.trim(),
      planned_due_date: createForm.planned_due_date.trim(),
      summary: createForm.summary.trim(),
    }),
    [createForm]
  );

  const handleCreate = useCallback(async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await metrologyApi.createRecord(createPayload);
      setCreateForm(initialForm);
      setSuccess('计量记录已创建');
      await loadRecords();
    } catch (err) {
      setError(err.message || '创建计量记录失败');
    } finally {
      setSaving(false);
    }
  }, [createPayload, loadRecords]);

  const handleAction = useCallback(
    async (item, action) => {
      setError('');
      setSuccess('');
      try {
        if (action === 'record') {
          await metrologyApi.recordResult(item.record_id, {
            performed_at_ms: Date.now(),
            result_status: 'passed',
            summary: item.summary || '计量完成',
            next_due_date: item.next_due_date || item.planned_due_date,
          });
        } else if (action === 'confirm') {
          await metrologyApi.confirmRecord(item.record_id, { notes: '确认完成' });
        } else if (action === 'approve') {
          await metrologyApi.approveRecord(item.record_id, { notes: '审批通过' });
        }
        setSuccess(`记录已处理: ${action}`);
        await loadRecords();
      } catch (err) {
        setError(err.message || '计量记录处理失败');
      }
    },
    [loadRecords]
  );

  const handleDispatch = useCallback(async () => {
    setDispatching(true);
    setError('');
    setSuccess('');
    try {
      const result = await metrologyApi.dispatchReminders(7);
      setSuccess(`已触发提醒 ${result.count || 0} 条`);
    } catch (err) {
      setError(err.message || '触发提醒失败');
    } finally {
      setDispatching(false);
    }
  }, []);

  return (
    <div
      data-testid="metrology-management-page"
      style={{ display: 'grid', gap: 16, padding: 20, background: '#f8fafc' }}
    >
      <div style={{ ...panelStyle, display: 'flex', justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>计量管理</h2>
        <button
          type="button"
          data-testid="metrology-dispatch-reminder"
          style={buttonStyle}
          onClick={handleDispatch}
          disabled={dispatching}
        >
          {dispatching ? '处理中...' : '触发 7 天内到期提醒'}
        </button>
      </div>

      {error ? (
        <div data-testid="metrology-error" style={{ ...panelStyle, color: '#9f1239' }}>
          {error}
        </div>
      ) : null}
      {success ? (
        <div data-testid="metrology-success" style={{ ...panelStyle, color: '#166534' }}>
          {success}
        </div>
      ) : null}

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>新建计量记录</h3>
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
          <input
            data-testid="metrology-create-equipment-id"
            style={inputStyle}
            placeholder="设备 ID"
            value={createForm.equipment_id}
            onChange={(event) => setCreateForm((p) => ({ ...p, equipment_id: event.target.value }))}
          />
          <input
            data-testid="metrology-create-responsible-user-id"
            style={inputStyle}
            placeholder="责任人 user_id"
            value={createForm.responsible_user_id}
            onChange={(event) =>
              setCreateForm((p) => ({ ...p, responsible_user_id: event.target.value }))
            }
          />
          <input
            data-testid="metrology-create-planned-due-date"
            style={inputStyle}
            placeholder="计划到期 YYYY-MM-DD"
            value={createForm.planned_due_date}
            onChange={(event) =>
              setCreateForm((p) => ({ ...p, planned_due_date: event.target.value }))
            }
          />
          <input
            data-testid="metrology-create-summary"
            style={inputStyle}
            placeholder="摘要"
            value={createForm.summary}
            onChange={(event) => setCreateForm((p) => ({ ...p, summary: event.target.value }))}
          />
        </div>
        <button
          type="button"
          data-testid="metrology-create-submit"
          style={{ ...primaryButtonStyle, marginTop: 10 }}
          disabled={saving}
          onClick={handleCreate}
        >
          {saving ? '创建中...' : '创建计量记录'}
        </button>
      </section>

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>计量记录列表</h3>
        {loading ? <div data-testid="metrology-loading">加载中...</div> : null}
        {!loading && records.length === 0 ? <div data-testid="metrology-empty">暂无计量记录</div> : null}
        <div style={{ display: 'grid', gap: 10 }}>
          {records.map((item) => (
            <div
              key={item.record_id}
              data-testid={`metrology-row-${item.record_id}`}
              style={{ border: '1px solid #d7dde5', borderRadius: 6, padding: 12 }}
            >
              <div>
                <strong>{item.record_id}</strong> · 设备 {item.equipment_id}
              </div>
              <div>状态: {item.status}</div>
              <div>计划到期: {item.planned_due_date}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                {(STATUS_ACTIONS[item.status] || []).map((action) => (
                  <button
                    key={action}
                    type="button"
                    data-testid={`metrology-action-${item.record_id}-${action}`}
                    style={buttonStyle}
                    onClick={() => handleAction(item, action)}
                  >
                    {action}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
