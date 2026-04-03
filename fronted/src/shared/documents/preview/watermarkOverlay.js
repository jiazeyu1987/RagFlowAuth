import React, { useMemo } from 'react';

const escapeXml = (value) =>
  String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

const toDataUrl = (svg) => `url("data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}")`;

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
      <span>{String(watermark?.label || '受控预览')}</span>
      <span style={{ fontWeight: 600 }}>禁止截图/外传</span>
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
    </div>
  );
}
