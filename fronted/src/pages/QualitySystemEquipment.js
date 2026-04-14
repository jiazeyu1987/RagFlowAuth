import React, { useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { QUALITY_CAPABILITY_ACTIONS } from '../shared/auth/capabilities';
import { useAuth } from '../hooks/useAuth';
import { QUALITY_SYSTEM_ROOT_PATH } from '../features/qualitySystem/moduleCatalog';
import EquipmentLifecycle from './EquipmentLifecycle';
import MetrologyManagement from './MetrologyManagement';
import MaintenanceManagement from './MaintenanceManagement';

const PANEL_STYLE = {
  background: '#ffffff',
  border: '1px solid #dbe2ea',
  borderRadius: '16px',
  padding: '18px',
  boxShadow: '0 10px 30px rgba(15, 23, 42, 0.06)',
};

const TAB_BUTTON_STYLE = (active) => ({
  border: active ? '1px solid #0f766e' : '1px solid #cbd5e1',
  borderRadius: '999px',
  background: active ? '#0f766e' : '#ffffff',
  color: active ? '#ffffff' : '#0f172a',
  cursor: 'pointer',
  padding: '8px 12px',
  fontWeight: 700,
});

const BASE_PATH = `${QUALITY_SYSTEM_ROOT_PATH}/equipment`;

const ROUTES = Object.freeze({
  equipment: BASE_PATH,
  metrology: `${BASE_PATH}/metrology`,
  maintenance: `${BASE_PATH}/maintenance`,
});

const resolveActiveTab = (pathname) => {
  const cleanPath = String(pathname || '').trim();
  if (cleanPath === ROUTES.metrology) return 'metrology';
  if (cleanPath === ROUTES.maintenance) return 'maintenance';
  return 'equipment';
};

const hasAnyCapability = (can, resource, actions) => (
  typeof can === 'function' && Array.isArray(actions) && actions.some((action) => can(resource, action))
);

export default function QualitySystemEquipment() {
  const location = useLocation();
  const navigate = useNavigate();
  const { can } = useAuth();

  const canEquipment = useMemo(
    () => hasAnyCapability(can, 'equipment_lifecycle', QUALITY_CAPABILITY_ACTIONS.equipment_lifecycle),
    [can]
  );
  const canMetrology = useMemo(
    () => hasAnyCapability(can, 'metrology', QUALITY_CAPABILITY_ACTIONS.metrology),
    [can]
  );
  const canMaintenance = useMemo(
    () => hasAnyCapability(can, 'maintenance', QUALITY_CAPABILITY_ACTIONS.maintenance),
    [can]
  );

  const activeTab = resolveActiveTab(location.pathname);
  const tabs = [
    { key: 'equipment', label: '设备台账', enabled: canEquipment, path: ROUTES.equipment },
    { key: 'metrology', label: '计量管理', enabled: canMetrology, path: ROUTES.metrology },
    { key: 'maintenance', label: '维护保养', enabled: canMaintenance, path: ROUTES.maintenance },
  ].filter((tab) => tab.enabled);

  const activeEnabled = tabs.some((tab) => tab.key === activeTab);

  return (
    <div
      data-testid="quality-system-equipment-page"
      style={{ display: 'grid', gap: 16, padding: 20, background: '#f8fafc' }}
    >
      <section style={PANEL_STYLE}>
        <h2 style={{ margin: 0 }}>设备与计量</h2>
        <p style={{ margin: '10px 0 0', color: '#475569', lineHeight: 1.6 }}>
          该工作区聚合设备全生命周期、计量管理与维护保养，并按质量 capability 控制可见与可操作范围。
        </p>
        <div style={{ marginTop: 14, display: 'flex', flexWrap: 'wrap', gap: 10 }}>
          {tabs.map((tab) => (
            <button
              key={tab.key}
              type="button"
              data-testid={`quality-system-equipment-tab-${tab.key}`}
              style={TAB_BUTTON_STYLE(activeTab === tab.key)}
              onClick={() => navigate(tab.path)}
            >
              {tab.label}
            </button>
          ))}
        </div>
      </section>

      {tabs.length === 0 ? (
        <section style={PANEL_STYLE} data-testid="quality-system-equipment-blocked">
          <h3 style={{ marginTop: 0 }}>缺少前提</h3>
          <div style={{ color: '#991b1b', lineHeight: 1.6 }}>
            当前账号没有设备/计量/维护相关 capability，无法进入该工作区。
          </div>
        </section>
      ) : !activeEnabled ? (
        <section style={PANEL_STYLE} data-testid="quality-system-equipment-tab-denied">
          <h3 style={{ marginTop: 0 }}>无法进入该子模块</h3>
          <div style={{ color: '#991b1b', lineHeight: 1.6 }}>
            当前账号缺少该子模块所需 capability。请选择上方有权限的入口。
          </div>
        </section>
      ) : activeTab === 'metrology' ? (
        <MetrologyManagement />
      ) : activeTab === 'maintenance' ? (
        <MaintenanceManagement />
      ) : (
        <EquipmentLifecycle />
      )}
    </div>
  );
}

