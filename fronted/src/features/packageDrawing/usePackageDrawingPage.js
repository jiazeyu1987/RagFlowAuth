import { useCallback, useMemo, useState } from 'react';
import packageDrawingApi from './api';
import { useAuth } from '../../hooks/useAuth';

const QUERY_TAB = 'query';
const IMPORT_TAB = 'import';

const mapApiError = (message) => {
  const code = String(message || '').trim();
  if (code === 'model_not_found') return '未找到该型号信息';
  if (code === 'only_xlsx_supported') return '仅支持 .xlsx 文件';
  if (code === 'file_required') return '请先选择导入文件';
  if (code === 'empty_file') return '文件内容为空';
  if (code.startsWith('invalid_xlsx')) return 'Excel 文件无法解析，请确认文件格式';
  return code || '操作失败';
};

export default function usePackageDrawingPage() {
  const { isAdmin } = useAuth();
  const admin = isAdmin();

  const [activeTab, setActiveTab] = useState(QUERY_TAB);
  const [model, setModel] = useState('');
  const [querying, setQuerying] = useState(false);
  const [queryResult, setQueryResult] = useState(null);
  const [queryError, setQueryError] = useState('');
  const [notFound, setNotFound] = useState(false);

  const [importFile, setImportFile] = useState(null);
  const [importing, setImporting] = useState(false);
  const [importResult, setImportResult] = useState(null);
  const [importError, setImportError] = useState('');

  const resultParameters = useMemo(() => {
    const source = queryResult?.parameters;
    if (!source || typeof source !== 'object') return [];
    return Object.entries(source);
  }, [queryResult]);

  const resultImages = useMemo(() => {
    const source = queryResult?.images;
    if (!Array.isArray(source)) return [];
    return source;
  }, [queryResult]);

  const handleTabChange = useCallback((nextTab) => {
    setActiveTab(nextTab);
  }, []);

  const handleQuerySubmit = useCallback(async (event) => {
    event?.preventDefault?.();
    const clean = String(model || '').trim();
    if (!clean) {
      setQueryError('请输入型号');
      setNotFound(false);
      setQueryResult(null);
      return;
    }

    setQuerying(true);
    setQueryError('');
    setNotFound(false);
    setQueryResult(null);
    try {
      const data = await packageDrawingApi.queryByModel(clean);
      setQueryResult(data);
    } catch (error) {
      const message = String(error?.message || '');
      if (message === 'model_not_found') {
        setNotFound(true);
      } else {
        setQueryError(mapApiError(message));
      }
    } finally {
      setQuerying(false);
    }
  }, [model]);

  const handleImportFileChange = useCallback((file) => {
    setImportFile(file || null);
  }, []);

  const handleImportSubmit = useCallback(async (event) => {
    event?.preventDefault?.();
    if (!importFile) {
      setImportError('请先选择 .xlsx 文件');
      setImportResult(null);
      return;
    }

    setImporting(true);
    setImportError('');
    setImportResult(null);
    try {
      const result = await packageDrawingApi.importExcel(importFile);
      setImportResult(result);
    } catch (error) {
      setImportError(mapApiError(error?.message));
    } finally {
      setImporting(false);
    }
  }, [importFile]);

  return {
    admin,
    activeTab,
    model,
    querying,
    queryResult,
    queryError,
    notFound,
    importing,
    importResult,
    importError,
    resultParameters,
    resultImages,
    setModel,
    handleTabChange,
    handleQuerySubmit,
    handleImportFileChange,
    handleImportSubmit,
    queryTab: QUERY_TAB,
    importTab: IMPORT_TAB,
  };
}
