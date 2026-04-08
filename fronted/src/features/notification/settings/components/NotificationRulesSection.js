import React from 'react';
import { card, cell, muted, primaryBtn, table } from '../pageStyles';

export default function NotificationRulesSection({
  title,
  description,
  rulesGroups,
  channelTypes,
  labels,
  rulesSaving,
  onSave,
  onToggleRule,
  warningText,
}) {
  return (
    <div style={card}>
      <form
        onSubmit={(event) => {
          event.preventDefault();
          onSave();
        }}
      >
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          <div>
            <h3 style={{ margin: 0 }}>{title}</h3>
            <div style={{ ...muted, marginTop: 6 }}>{description}</div>
          </div>
          <button type="submit" data-testid="notification-save-rules" style={primaryBtn} disabled={rulesSaving}>
            {rulesSaving ? '保存中...' : '保存通知规则'}
          </button>
        </div>
        <div style={{ display: 'grid', gap: 16, marginTop: 16 }}>
          {(rulesGroups || []).map((group) => (
            <div key={group.group_key} style={{ border: '1px solid #e5e7eb', borderRadius: 14, overflow: 'hidden' }}>
              <div style={{ padding: '14px 16px', borderBottom: '1px solid #e5e7eb', background: '#f9fafb', fontWeight: 700 }}>
                {group.group_label}
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table style={table}>
                  <thead>
                    <tr>
                      <th style={cell}>事件</th>
                      <th style={cell}>邮件</th>
                      <th style={cell}>钉钉</th>
                      <th style={cell}>站内信</th>
                      <th style={cell}>风险</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(group.items || []).map((item) => (
                      <tr key={item.event_type}>
                        <td style={cell}>
                          <div style={{ fontWeight: 600 }}>{item.event_label}</div>
                          <div style={muted}>{item.event_type}</div>
                        </td>
                        {channelTypes.map((channelType) => (
                          <td key={`${item.event_type}-${channelType}`} style={cell}>
                            <label style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
                              <input
                                type="checkbox"
                                data-testid={`notification-rule-${item.event_type}-${channelType}`}
                                checked={(item.enabled_channel_types || []).includes(channelType)}
                                onChange={() => onToggleRule(item.event_type, channelType)}
                              />
                              <span>{labels[channelType]}</span>
                            </label>
                          </td>
                        ))}
                        <td style={cell}>
                          {warningText(item) ? (
                            <span style={{ color: '#92400e' }}>{warningText(item)}</span>
                          ) : (
                            <span style={{ color: '#047857' }}>已配置</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ))}
        </div>
      </form>
    </div>
  );
}
