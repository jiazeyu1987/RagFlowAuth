import React from 'react';
import { formatTime } from '../documentAuditHelpers';
import {
  MANIFEST_LABEL_STYLE,
  MANIFEST_VALUE_STYLE,
  VERIFIED_TEXT,
} from '../documentAuditView';

export default function DocumentAuditSignatureManifest({ item }) {
  if (!item?.signature_id) {
    return <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>-</span>;
  }

  return (
    <div style={{ display: 'grid', gap: '6px' }}>
      <div>
        <div style={MANIFEST_LABEL_STYLE}>签名人</div>
        <div style={MANIFEST_VALUE_STYLE}>
          {item.signed_by_full_name ||
            item.signed_by_username ||
            item.reviewed_by_name ||
            item.reviewed_by ||
            '-'}
        </div>
      </div>
      <div>
        <div style={MANIFEST_LABEL_STYLE}>签名时间</div>
        <div style={MANIFEST_VALUE_STYLE}>{formatTime(item.signed_at_ms)}</div>
      </div>
      <div>
        <div style={MANIFEST_LABEL_STYLE}>签名含义</div>
        <div style={MANIFEST_VALUE_STYLE}>{item.signature_meaning || '-'}</div>
      </div>
      <div>
        <div style={MANIFEST_LABEL_STYLE}>签署原因</div>
        <div style={MANIFEST_VALUE_STYLE}>{item.signature_reason || '-'}</div>
      </div>
      <div>
        <div style={MANIFEST_LABEL_STYLE}>签名 ID</div>
        <div
          style={{
            ...MANIFEST_VALUE_STYLE,
            fontFamily:
              "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
          }}
        >
          {item.signature_id}
        </div>
      </div>
      <div>
        <div style={MANIFEST_LABEL_STYLE}>验签结果</div>
        <div
          style={{
            ...MANIFEST_VALUE_STYLE,
            color:
              item.signature_verified === true
                ? '#166534'
                : item.signature_verified === false
                  ? '#b91c1c'
                  : MANIFEST_VALUE_STYLE.color,
            fontWeight: 600,
          }}
        >
          {item.signature_verified === true
            ? VERIFIED_TEXT.yes
            : item.signature_verified === false
              ? VERIFIED_TEXT.no
              : VERIFIED_TEXT.unknown}
        </div>
      </div>
    </div>
  );
}

