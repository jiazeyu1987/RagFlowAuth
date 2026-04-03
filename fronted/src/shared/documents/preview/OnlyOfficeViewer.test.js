import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import OnlyOfficeViewer from './OnlyOfficeViewer';

describe('OnlyOfficeViewer', () => {
  const watermark = {
    label: '\u53d7\u63a7\u9884\u89c8',
    text: '\u7528\u6237:tester | \u516c\u53f8:QA Org | \u65f6\u95f4:2026-04-03 10:00:00 CST | \u6587\u6863ID:doc-1',
    username: 'tester',
    company: 'QA Org',
    timestamp: '2026-04-03 10:00:00 CST',
  };

  beforeEach(() => {
    document.body.innerHTML = '';
    const script = document.createElement('script');
    script.id = 'onlyoffice-docsapi-http___onlyoffice_local';
    document.body.appendChild(script);
    window.DocsAPI = {
      DocEditor: function DocEditor() {
        this.destroyEditor = function destroyEditor() {};
      },
    };
  });

  afterEach(() => {
    delete window.DocsAPI;
  });

  it('renders overlay and corner watermark when onlyoffice watermark exists', async () => {
    render(
      <OnlyOfficeViewer
        serverUrl="http://onlyoffice.local"
        config={{ document: { title: 'report.docx' } }}
        watermark={watermark}
        height="300px"
      />
    );

    await waitFor(() => {
      expect(screen.getByTestId('preview-watermark-overlay')).toBeInTheDocument();
    });
    expect(screen.getByTestId('preview-corner-watermark')).toHaveTextContent(
      '\u53d7\u63a7\u9884\u89c8'
    );
    expect(screen.getByTestId('preview-corner-watermark')).toHaveTextContent('tester');
  });
});
