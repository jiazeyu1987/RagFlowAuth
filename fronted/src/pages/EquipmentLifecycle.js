import React, { useCallback, useEffect, useMemo, useState } from 'react';
import equipmentApi from '../features/equipment/api';

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
  asset_code: '',
  equipment_name: '',
  owner_user_id: '',
  location: '',
  supplier_name: '',
  purchase_date: '',
  retirement_due_date: '',
  next_metrology_due_date: '',
  next_maintenance_due_date: '',
  notes: '',
};

const STATUS_ACTIONS = {
  purchased: ['accept'],
  accepted: ['commission'],
  in_service: ['retire'],
  under_maintenance: ['retire'],
  under_metrology: ['retire'],
};

export default function EquipmentLifecycle() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [dispatching, setDispatching] = useState(false);
  const [assets, setAssets] = useState([]);
  const [createForm, setCreateForm] = useState(initialForm);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const loadAssets = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const next = await equipmentApi.listAssets({ limit: 100 });
      setAssets(next);
    } catch (err) {
      setError(err.message || '加载设备列表失败');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadAssets();
  }, [loadAssets]);

  const createPayload = useMemo(
    () => ({
      asset_code: createForm.asset_code.trim(),
      equipment_name: createForm.equipment_name.trim(),
      owner_user_id: createForm.owner_user_id.trim(),
      location: createForm.location.trim() || undefined,
      supplier_name: createForm.supplier_name.trim() || undefined,
      purchase_date: createForm.purchase_date.trim() || undefined,
      retirement_due_date: createForm.retirement_due_date.trim() || undefined,
      next_metrology_due_date: createForm.next_metrology_due_date.trim() || undefined,
      next_maintenance_due_date: createForm.next_maintenance_due_date.trim() || undefined,
      notes: createForm.notes.trim() || undefined,
    }),
    [createForm]
  );

  const handleCreate = useCallback(async () => {
    setSaving(true);
    setError('');
    setSuccess('');
    try {
      await equipmentApi.createAsset(createPayload);
      setCreateForm(initialForm);
      setSuccess('设备已创建');
      await loadAssets();
    } catch (err) {
      setError(err.message || '创建设备失败');
    } finally {
      setSaving(false);
    }
  }, [createPayload, loadAssets]);

  const handleTransition = useCallback(
    async (equipmentId, action) => {
      setError('');
      setSuccess('');
      try {
        if (action === 'accept') {
          await equipmentApi.acceptAsset(equipmentId);
        } else if (action === 'commission') {
          await equipmentApi.commissionAsset(equipmentId);
        } else if (action === 'retire') {
          await equipmentApi.retireAsset(equipmentId);
        }
        setSuccess(`状态已更新: ${action}`);
        await loadAssets();
      } catch (err) {
        setError(err.message || '更新设备状态失败');
      }
    },
    [loadAssets]
  );

  const handleDispatch = useCallback(async () => {
    setDispatching(true);
    setError('');
    setSuccess('');
    try {
      const result = await equipmentApi.dispatchReminders(7);
      setSuccess(`已触发提醒 ${result.count || 0} 条`);
    } catch (err) {
      setError(err.message || '触发提醒失败');
    } finally {
      setDispatching(false);
    }
  }, []);

  return (
    <div
      data-testid="equipment-lifecycle-page"
      style={{ display: 'grid', gap: 16, padding: 20, background: '#f8fafc' }}
    >
      <div style={{ ...panelStyle, display: 'flex', justifyContent: 'space-between' }}>
        <h2 style={{ margin: 0 }}>设备全生命周期</h2>
        <button
          type="button"
          data-testid="equipment-dispatch-reminder"
          style={buttonStyle}
          onClick={handleDispatch}
          disabled={dispatching}
        >
          {dispatching ? '处理中...' : '触发 7 天内到期提醒'}
        </button>
      </div>

      {error ? (
        <div data-testid="equipment-error" style={{ ...panelStyle, color: '#9f1239' }}>
          {error}
        </div>
      ) : null}
      {success ? (
        <div data-testid="equipment-success" style={{ ...panelStyle, color: '#166534' }}>
          {success}
        </div>
      ) : null}

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>创建设备台账</h3>
        <div style={{ display: 'grid', gap: 10, gridTemplateColumns: 'repeat(3, minmax(0, 1fr))' }}>
          <input
            data-testid="equipment-create-asset-code"
            style={inputStyle}
            placeholder="资产编码"
            value={createForm.asset_code}
            onChange={(event) => setCreateForm((p) => ({ ...p, asset_code: event.target.value }))}
          />
          <input
            data-testid="equipment-create-name"
            style={inputStyle}
            placeholder="设备名称"
            value={createForm.equipment_name}
            onChange={(event) => setCreateForm((p) => ({ ...p, equipment_name: event.target.value }))}
          />
          <input
            data-testid="equipment-create-owner-user-id"
            style={inputStyle}
            placeholder="责任人编号"
            value={createForm.owner_user_id}
            onChange={(event) => setCreateForm((p) => ({ ...p, owner_user_id: event.target.value }))}
          />
          <input
            data-testid="equipment-create-location"
            style={inputStyle}
            placeholder="位置"
            value={createForm.location}
            onChange={(event) => setCreateForm((p) => ({ ...p, location: event.target.value }))}
          />
          <input
            data-testid="equipment-create-supplier"
            style={inputStyle}
            placeholder="供应商"
            value={createForm.supplier_name}
            onChange={(event) => setCreateForm((p) => ({ ...p, supplier_name: event.target.value }))}
          />
          <input
            data-testid="equipment-create-purchase-date"
            style={inputStyle}
            placeholder="采购日期（年-月-日）"
            value={createForm.purchase_date}
            onChange={(event) => setCreateForm((p) => ({ ...p, purchase_date: event.target.value }))}
          />
          <input
            data-testid="equipment-create-retirement-due-date"
            style={inputStyle}
            placeholder="报废日期（年-月-日）"
            value={createForm.retirement_due_date}
            onChange={(event) =>
              setCreateForm((p) => ({ ...p, retirement_due_date: event.target.value }))
            }
          />
          <input
            data-testid="equipment-create-metrology-due-date"
            style={inputStyle}
            placeholder="下次计量日期（年-月-日）"
            value={createForm.next_metrology_due_date}
            onChange={(event) =>
              setCreateForm((p) => ({ ...p, next_metrology_due_date: event.target.value }))
            }
          />
          <input
            data-testid="equipment-create-maintenance-due-date"
            style={inputStyle}
            placeholder="下次维护日期（年-月-日）"
            value={createForm.next_maintenance_due_date}
            onChange={(event) =>
              setCreateForm((p) => ({ ...p, next_maintenance_due_date: event.target.value }))
            }
          />
        </div>
        <textarea
          data-testid="equipment-create-notes"
          style={{ ...inputStyle, marginTop: 10, minHeight: 80 }}
          placeholder="备注"
          value={createForm.notes}
          onChange={(event) => setCreateForm((p) => ({ ...p, notes: event.target.value }))}
        />
        <button
          type="button"
          data-testid="equipment-create-submit"
          style={{ ...primaryButtonStyle, marginTop: 10 }}
          disabled={saving}
          onClick={handleCreate}
        >
          {saving ? '创建中...' : '创建设备'}
        </button>
      </section>

      <section style={panelStyle}>
        <h3 style={{ marginTop: 0 }}>设备列表</h3>
        {loading ? <div data-testid="equipment-loading">加载中...</div> : null}
        {!loading && assets.length === 0 ? <div data-testid="equipment-empty">暂无设备</div> : null}
        <div style={{ display: 'grid', gap: 10 }}>
          {assets.map((item) => (
            <div
              key={item.equipment_id}
              data-testid={`equipment-row-${item.equipment_id}`}
              style={{ border: '1px solid #d7dde5', borderRadius: 6, padding: 12 }}
            >
              <div>
                <strong>{item.asset_code}</strong> · {item.equipment_name}
              </div>
              <div>状态: {item.status}</div>
              <div>责任人: {item.owner_user_id}</div>
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                {(STATUS_ACTIONS[item.status] || []).map((action) => (
                  <button
                    key={action}
                    type="button"
                    data-testid={`equipment-action-${item.equipment_id}-${action}`}
                    style={buttonStyle}
                    onClick={() => handleTransition(item.equipment_id, action)}
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
