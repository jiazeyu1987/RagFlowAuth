export const TABLE_PREVIEW_STYLE_ID = 'table-preview-styles';

export const ensureTablePreviewStyles = () => {
  if (typeof document === 'undefined') return;
  if (document.getElementById(TABLE_PREVIEW_STYLE_ID)) return;

  const style = document.createElement('style');
  style.id = TABLE_PREVIEW_STYLE_ID;
  style.textContent = `
    .table-preview table {
      border-collapse: collapse;
      width: 100%;
      font-size: 0.875rem;
    }
    .table-preview th,
    .table-preview td {
      border: 1px solid #d1d5db;
      padding: 8px 12px;
      text-align: left;
    }
    .table-preview th {
      background-color: #f3f4f6;
      font-weight: 600;
      color: #1f2937;
    }
    .table-preview tr:nth-child(even) {
      background-color: #f9fafb;
    }
    .table-preview tr:hover {
      background-color: #f3f4f6;
    }
  `;
  document.head.appendChild(style);
};

