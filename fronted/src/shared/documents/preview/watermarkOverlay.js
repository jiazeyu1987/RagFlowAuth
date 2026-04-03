import React, { useMemo } from 'react';

const escapeXml = (value) =>
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const toDataUrl = (svg) => `url("data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}")`;

const truncate = (value, maxLength = 96) => {
  const text = String(value || '').trim();
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return `${text.slice(0, Math.max(0, maxLength - 1))}...`;
};

const compactTime = (value) => String(value || '').trim().replace(/\s+[A-Z]{2,5}$/, '');

const buildWatermarkSvg = (watermark) => {
  const overlay = watermark?.overlay || {};
  const width = Math.max(Number(overlay?.gap_x) || 260, 180);
  const height = Math.max(Number(overlay?.gap_y) || 180, 120);
  const rotationDeg = Number(overlay?.rotation_deg) || -24;
  const fontSize = Math.max(Number(overlay?.font_size) || 18, 12);
  const opacity = Number(overlay?.opacity);
  const fillOpacity = Number.isFinite(opacity) ? Math.min(Math.max(opacity, 0.08), 0.4) : 0.18;
  const textColor = String(overlay?.text_color || '#6b7280');
  const text = escapeXml(watermark?.text || '');

  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
      <g transform="translate(${Math.round(width * 0.14)} ${Math.round(height * 0.62)}) rotate(${rotationDeg})">
        <text
          x="0"
          y="0"
          font-size="${fontSize}"
          font-family="Segoe UI, PingFang SC, Microsoft YaHei, sans-serif"
          fill="${textColor}"
          fill-opacity="${fillOpacity}"
        >${text}</text>
      </g>
    </svg>
  `;
};

export function WatermarkOverlay({ watermark, testId = 'preview-watermark-overlay' }) {
  const watermarkText = String(watermark?.text || '').trim();
  const backgroundImage = useMemo(() => {
    if (!watermarkText) return '';
    return toDataUrl(buildWatermarkSvg(watermark));
  }, [watermark, watermarkText]);

  if (!watermarkText) return null;

  return (
    <div
      aria-hidden="true"
      data-testid={testId}
      data-watermark-text={watermarkText}
      style={{
        position: 'absolute',
        inset: 0,
        pointerEvents: 'none',
        backgroundImage,
        backgroundRepeat: 'repeat',
        backgroundPosition: '0 0',
        zIndex: 5,
      }}
    />
  );
}

export function ControlledPreviewBadge({ watermark }) {
  if (!String(watermark?.text || '').trim()) return null;

  return (
    <div
      data-testid="preview-controlled-badge"
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '8px',
        padding: '6px 10px',
        borderRadius: '999px',
        background: '#fff7ed',
        border: '1px solid #fdba74',
        color: '#9a3412',
        fontSize: '0.82rem',
        fontWeight: 700,
        whiteSpace: 'nowrap',
      }}
    >
      <span>{String(watermark?.label || '\u53d7\u63a7\u9884\u89c8')}</span>
      <span style={{ fontWeight: 600 }}>{'\u7981\u6b62\u622a\u56fe/\u5916\u4f20'}</span>
    </div>
  );
}

export function CornerWatermarkBadge({ watermark }) {
  const watermarkText = String(watermark?.text || '').trim();
  if (!watermarkText) return null;

  const label =
    String(watermark?.label || '\u53d7\u63a7\u9884\u89c8').trim() || '\u53d7\u63a7\u9884\u89c8';
  const actorName = String(watermark?.actor_name || watermark?.username || '').trim();
  const actorAccount = String(watermark?.actor_account || '').trim();
  const actorTime = compactTime(watermark?.timestamp);
  const actorIdentity = actorAccount || actorName;
  const detailParts = [actorIdentity, actorTime].filter(Boolean);
  const detail = truncate(detailParts.join(' | ') || watermarkText, 120);

  return (
    <div
      aria-hidden="true"
      data-testid="preview-corner-watermark"
      data-watermark-label={label}
      data-watermark-detail={detail}
      style={{
        position: 'absolute',
        right: '16px',
        bottom: '16px',
        maxWidth: 'min(420px, calc(100% - 32px))',
        padding: '10px 14px',
        borderRadius: '14px',
        background: 'rgba(55, 65, 81, 0.58)',
        border: '1px solid rgba(251, 191, 36, 0.9)',
        color: '#f9fafb',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        boxShadow: '0 12px 28px rgba(15, 23, 42, 0.28)',
        pointerEvents: 'none',
        userSelect: 'none',
        zIndex: 7,
        backdropFilter: 'blur(6px)',
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
          minWidth: 0,
        }}
      >
        <span
          style={{
            fontSize: '0.9rem',
            fontWeight: 800,
            color: '#fcd34d',
            whiteSpace: 'nowrap',
          }}
        >
          {label}
        </span>
        <span
          style={{
            fontSize: '0.8rem',
            fontWeight: 700,
            color: '#fdba74',
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            flexShrink: 0,
          }}
        >
          {'\u7981\u6b62\u622a\u56fe/\u5916\u4f20'}
        </span>
      </div>
      <div
        style={{
          fontSize: '0.82rem',
          lineHeight: 1.45,
          color: 'rgba(255, 255, 255, 0.92)',
          wordBreak: 'break-all',
        }}
      >
        {detail}
      </div>
    </div>
  );
}

export function WatermarkedPreviewFrame({ watermark, children, height = '100%' }) {
  return (
    <div
      style={{
        position: 'relative',
        minHeight: height,
      }}
    >
      {children}
      <WatermarkOverlay watermark={watermark} />
      <CornerWatermarkBadge watermark={watermark} />
    </div>
  );
}
