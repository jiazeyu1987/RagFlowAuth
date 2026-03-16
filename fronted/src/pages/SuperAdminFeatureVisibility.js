import React, { useEffect, useMemo, useState } from 'react';
import { httpClient } from '../shared/http/httpClient';
import { normalizeDisplayError } from '../shared/utils/displayError';

const FIELD_META = [
  { key: 'tool_nhsa_visible', title: '医保编码查询工具', desc: '实用工具页中的医保编码外链工具卡' },
  { key: 'tool_sh_tax_visible', title: '上海电子税务局入口', desc: '实用工具页中的税务外链工具卡' },
  { key: 'tool_drug_admin_visible', title: '药监导航页面', desc: '药监导航工具页及其后端接口' },
  { key: 'tool_nmpa_visible', title: 'NMPA 页面', desc: 'NMPA 工具页入口' },
  { key: 'tool_nas_visible', title: 'NAS 网盘页面', desc: 'NAS 页面及 NAS 导入任务接口' },
  { key: 'page_data_security_test_visible', title: '数据安全测试页', desc: '数据安全测试页面入口' },
  { key: 'page_logs_visible', title: '日志审计页', desc: '日志审计页面入口' },
  { key: 'api_audit_events_visible', title: '审计事件接口', desc: '审计事件接口可见性' },
  { key: 'api_diagnostics_visible', title: '系统诊断接口', desc: '系统诊断接口可见性' },
  { key: 'api_admin_feature_flags_visible', title: '安全功能开关接口', desc: '安全功能开关接口可见性' },
];

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
      setError(normalizeDisplayError(e?.message ?? e, '加载失败'));
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
      setError(normalizeDisplayError(e?.message ?? e, '保存失败'));
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="medui-empty" data-testid="super-admin-feature-loading">加载中...</div>;
  }

  return (
    <div className="admin-med-page" data-testid="super-admin-feature-page">
      <section className="medui-surface medui-card-pad">
        <h2 className="admin-med-title" style={{ marginTop: 0, marginBottom: 6 }}>超级管理员可见性控制</h2>
        <div className="admin-med-inline-note">
          关闭后，普通管理员与业务用户将看不到功能入口，相关后端接口也会被隐藏。
        </div>
      </section>

      <section className="medui-surface medui-card-pad">
        <div className="admin-med-flag-grid">
          {items.map((item) => (
            <label key={item.key} className="admin-med-flag-item">
              <input
                type="checkbox"
                checked={item.enabled}
                onChange={(e) => onToggle(item.key, e.target.checked)}
                data-testid={`super-admin-flag-${item.key}`}
              />
              <div>
                <div style={{ fontWeight: 700, color: '#16324d' }}>{item.title}</div>
                <div className="admin-med-small" style={{ marginTop: 2 }}>{item.desc}</div>
              </div>
            </label>
          ))}
        </div>

        <div className="admin-med-actions" style={{ marginTop: 14 }}>
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            data-testid="super-admin-feature-save"
            className="medui-btn medui-btn--primary"
          >
            {saving ? '保存中...' : '保存配置'}
          </button>
          <button
            type="button"
            onClick={load}
            disabled={saving}
            data-testid="super-admin-feature-reload"
            className="medui-btn medui-btn--secondary"
          >
            重新加载
          </button>
        </div>

        {error ? <div data-testid="super-admin-feature-error" className="admin-med-danger" style={{ marginTop: 12 }}>{error}</div> : null}
        {message ? <div data-testid="super-admin-feature-message" className="admin-med-success" style={{ marginTop: 12 }}>{message}</div> : null}
      </section>
    </div>
  );
};

export default SuperAdminFeatureVisibility;
