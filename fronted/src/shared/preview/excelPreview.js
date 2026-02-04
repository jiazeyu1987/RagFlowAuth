import * as XLSX from 'xlsx';

export const DEFAULT_MAX_SHEETS = 20;

export const isExcelFilename = (name) => {
  const n = String(name || '').toLowerCase().trim();
  return n.endsWith('.xlsx') || n.endsWith('.xls');
};

export const excelArrayBufferToSheetsHtml = (arrayBuffer, { maxSheets = DEFAULT_MAX_SHEETS } = {}) => {
  const workbook = XLSX.read(arrayBuffer, { type: 'array' });
  const sheetNames = (workbook.SheetNames || []).slice(0, maxSheets);
  const sheets = {};
  for (const sheetName of sheetNames) {
    const worksheet = workbook.Sheets[sheetName];
    sheets[sheetName] = XLSX.utils.sheet_to_html(worksheet);
  }
  return { sheets, sheetNames, truncated: (workbook.SheetNames || []).length > sheetNames.length };
};

export const excelBlobToSheetsHtml = async (blob, opts) => {
  const arrayBuffer = await blob.arrayBuffer();
  return excelArrayBufferToSheetsHtml(arrayBuffer, opts);
};

