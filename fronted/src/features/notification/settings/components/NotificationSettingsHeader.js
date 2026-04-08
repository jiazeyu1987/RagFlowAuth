import React from 'react';
import { btn, muted, primaryBtn } from '../pageStyles';

export default function NotificationSettingsHeader({
  title,
  description,
  activeTab,
  onChangeTab,
  tabs,
}) {
  const hasMeta = Boolean(title || description);
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: hasMeta ? 'space-between' : 'flex-end',
        gap: 12,
        flexWrap: 'wrap',
        alignItems: 'center',
      }}
    >
      {hasMeta ? (
        <div>
          <h2 style={{ margin: 0 }}>{title}</h2>
          <div style={{ ...muted, marginTop: 6 }}>{description}</div>
        </div>
      ) : null}
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
        {tabs.map((tab) => (
          <button
            key={tab.value}
            type="button"
            data-testid={tab.testId}
            style={activeTab === tab.value ? primaryBtn : btn}
            onClick={() => onChangeTab(tab.value)}
          >
            {tab.label}
          </button>
        ))}
      </div>
    </div>
  );
}
