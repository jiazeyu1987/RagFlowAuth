import React from 'react';
import { render, screen } from '@testing-library/react';
import { CornerWatermarkBadge, WatermarkedPreviewFrame } from './watermarkOverlay';

describe('watermarkOverlay', () => {
  const watermark = {
    label: '\u53d7\u63a7\u9884\u89c8',
    text: '\u7528\u6237:tester | \u516c\u53f8:QA Org | \u65f6\u95f4:2026-04-03 10:00:00 CST | \u6587\u6863ID:doc-1',
    username: 'tester',
    actor_name: '\u6d4b\u8bd5\u7528\u6237',
    actor_account: 'tester',
    company: 'QA Org',
    timestamp: '2026-04-03 10:00:00 CST',
    overlay: {
      text_color: '#6b7280',
      opacity: 0.18,
      rotation_deg: -24,
      gap_x: 260,
      gap_y: 180,
      font_size: 18,
    },
  };

  it('renders both repeated overlay and corner badge in preview frame', () => {
    render(
      <WatermarkedPreviewFrame watermark={watermark} height="300px">
        <div>preview body</div>
      </WatermarkedPreviewFrame>
    );

    expect(screen.getByTestId('preview-watermark-overlay')).toHaveAttribute(
      'data-watermark-text',
      expect.stringContaining('doc-1')
    );
    expect(screen.getByTestId('preview-corner-watermark')).toHaveAttribute(
      'data-watermark-label',
      '\u53d7\u63a7\u9884\u89c8'
    );
    expect(screen.getByTestId('preview-corner-watermark')).toHaveTextContent(
      '\u7981\u6b62\u622a\u56fe/\u5916\u4f20'
    );
    expect(screen.getByTestId('preview-corner-watermark')).toHaveTextContent('tester');
    expect(screen.getByTestId('preview-corner-watermark')).not.toHaveTextContent('\u6d4b\u8bd5\u7528\u6237');
    expect(screen.getByTestId('preview-corner-watermark')).toHaveTextContent('2026-04-03 10:00:00');
    expect(screen.getByTestId('preview-corner-watermark')).not.toHaveTextContent('QA Org');
  });

  it('does not render corner badge when watermark text is empty', () => {
    render(<CornerWatermarkBadge watermark={{ ...watermark, text: '   ' }} />);
    expect(screen.queryByTestId('preview-corner-watermark')).not.toBeInTheDocument();
  });

  it('truncates long corner detail text', () => {
    render(
      <CornerWatermarkBadge
        watermark={{
          ...watermark,
          actor_name: 'very-long-display-name-for-preview-watermark',
          actor_account: 'very-long-user-name-for-preview-watermark-with-extra-suffix-to-force-truncation-in-badge',
          timestamp: '2026-04-03 10:00:00 CST and more text to force truncation in badge detail',
        }}
      />
    );

    const badge = screen.getByTestId('preview-corner-watermark');
    expect(badge.getAttribute('data-watermark-detail')).toContain('...');
  });
});
