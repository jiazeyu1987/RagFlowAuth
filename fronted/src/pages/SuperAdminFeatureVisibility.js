import React, { useEffect, useMemo, useState } from 'react';
import { httpClient } from '../shared/http/httpClient';

const FIELD_META = [
  { key: 'tool_nhsa_visible', title: '医保编码查询工具', desc: '实用工具页中的医保编码外链卡片' },
  { key: 'tool_sh_tax_visible', title: '上海电子税务局入口', desc: '实用工具页中的税务外链卡片' },
  { key: 'tool_drug_admin_visible', title: '药监导航页面', desc: '药监导航工具页及其后端接口' },
  { key: 'tool_nmpa_visible', title: 'NMPA 页面', desc: 'NMPA 工具页入口' },
  { key: 'tool_nas_visible', title: 'NAS 网盘页面', desc: 'NAS 页面及 NAS 导入任务接口' },
  { key: 'page_data_security_test_visible', title: '数据安全测试页', desc: 'data-security-test 路由' },
  { key: 'page_logs_visible', title: '日志审计页', desc: '前端日志审计页面入口' },
  { key: 'api_audit_events_visible', title: '审计事件接口', desc: '/api/audit/events 接口可见性' },
  { key: 'api_diagnostics_visible', title: '系统诊断接口', desc: '/api/diagnostics/* 接口可见性' },
  { key: 'api_admin_feature_flags_visible', title: '安全功能开关接口', desc: '/api/admin/security/feature-flags* 接口可见性' },
];

const cardStyle = {
  background: '#fff',
  border: '1px solid #e5e7eb',
  borderRadius: 12,
  padding: 16,
};

const pageStyle = {
  maxWidth: 960,
  display: 'grid',
  gap: 16,
};

const SuperAdminFeatureVisibility = () => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [flags, setFlags] = useState({});

  const items = useMemo(
    () =>
      FIELD_META.map((item) => ({
        ...item,
        enabled: flags?.[item.key] !== false,
      })),
    [flags]
  );

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const payload = await httpClient.requestJson('/api/super-admin/feature-visibility');
      setFlags(payload && typeof payload === 'object' ? payload : {});
    } catch (e) {
      setError(e?.message || '加载失败');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const onToggle = (key, enabled) => {
    setFlags((prev) => ({ ...(prev || {}), [key]: enabled }));
  };

  const onSave = async () => {
    setSaving(true);
    setError('');
    setMessage('');
    try {
      const payload = await httpClient.requestJson('/api/super-admin/feature-visibility', {
        method: 'PUT',
        body: JSON.stringify(flags || {}),
      });
      setFlags(payload && typeof payload === 'object' ? payload : {});
      setMessage('保存成功，刷新后立即生效');
    } catch (e) {
      setError(e?.message || '保存失败');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div data-testid="super-admin-feature-loading">加载中...</div>;
  }

  return (
    <div style={pageStyle} data-testid="super-admin-feature-page">
      <div style={cardStyle}>
        <h2 style={{ marginTop: 0, marginBottom: 6 }}>超级管理员功能隐藏控制</h2>
        <div style={{ color: '#6b7280' }}>
          关闭后，普通管理员与业务用户将看不到该功能入口，相关后端接口也会被隐藏。
        </div>
      </div>

      <div style={cardStyle}>
        <div style={{ display: 'grid', gap: 10 }}>
          {items.map((item) => (
            <label
              key={item.key}
              style={{
                display: 'grid',
                gridTemplateColumns: '24px 1fr',
                gap: 10,
                alignItems: 'start',
                padding: '8px 0',
                borderBottom: '1px dashed #e5e7eb',
              }}
            >
              <input
                type="checkbox"
                checked={item.enabled}
                onChange={(e) => onToggle(item.key, e.target.checked)}
                data-testid={`super-admin-flag-${item.key}`}
              />
              <div>
                <div style={{ fontWeight: 700, color: '#111827' }}>{item.title}</div>
                <div style={{ marginTop: 3, color: '#6b7280', fontSize: 13 }}>{item.desc}</div>
              </div>
            </label>
          ))}
        </div>

        <div style={{ marginTop: 16, display: 'flex', gap: 10, alignItems: 'center' }}>
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            data-testid="super-admin-feature-save"
            style={{
              padding: '10px 14px',
              border: 'none',
              borderRadius: 8,
              background: saving ? '#9ca3af' : '#111827',
              color: '#fff',
              cursor: saving ? 'not-allowed' : 'pointer',
            }}
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
          <button
            type="button"
            onClick={load}
            disabled={saving}
            data-testid="super-admin-feature-reload"
            style={{
              padding: '10px 14px',
              border: '1px solid #d1d5db',
              borderRadius: 8,
              background: '#fff',
              color: '#111827',
              cursor: saving ? 'not-allowed' : 'pointer',
            }}
          >
            重新加载
          </button>
        </div>

        {error ? (
          <div data-testid="super-admin-feature-error" style={{ marginTop: 12, color: '#b91c1c' }}>
            {error}
          </div>
        ) : null}
        {message ? (
          <div data-testid="super-admin-feature-message" style={{ marginTop: 12, color: '#166534' }}>
            {message}
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default SuperAdminFeatureVisibility;
