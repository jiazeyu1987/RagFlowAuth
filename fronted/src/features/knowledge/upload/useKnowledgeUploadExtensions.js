import { useEffect, useMemo, useState } from 'react';

import { knowledgeUploadApi } from './api';
import { mapUserFacingErrorMessage } from '../../../shared/errors/userFacingErrorMessages';
import { normalizeExtension } from './utils';

export default function useKnowledgeUploadExtensions({ canManageExtensions }) {
  const [allowedExtensions, setAllowedExtensions] = useState([]);
  const [loadingExtensions, setLoadingExtensions] = useState(true);
  const [savingExtensions, setSavingExtensions] = useState(false);
  const [extensionDraft, setExtensionDraft] = useState('');
  const [extensionsMessage, setExtensionsMessage] = useState(null);

  const acceptAttr = useMemo(() => {
    const values = Array.isArray(allowedExtensions) ? allowedExtensions : [];
    return values.join(',');
  }, [allowedExtensions]);

  const extensionSet = useMemo(() => new Set(allowedExtensions), [allowedExtensions]);

  useEffect(() => {
    let active = true;

    const fetchAllowedExtensions = async () => {
      try {
        setLoadingExtensions(true);
        const payload = await knowledgeUploadApi.getAllowedExtensions();
        if (!active) return;

        const normalizedExtensions = payload.allowedExtensions
          .map(normalizeExtension)
          .filter(Boolean);

        setAllowedExtensions(Array.from(new Set(normalizedExtensions)).sort());
        setExtensionsMessage(null);
      } catch (requestError) {
        if (!active) return;
        setAllowedExtensions([]);
        setExtensionsMessage({
          type: 'error',
          text: mapUserFacingErrorMessage(
            requestError?.message,
            '无法加载可上传文件后缀，已回退到默认配置'
          ),
        });
      } finally {
        if (active) {
          setLoadingExtensions(false);
        }
      }
    };

    fetchAllowedExtensions();

    return () => {
      active = false;
    };
  }, []);

  const handleAddExtension = () => {
    const normalizedExtension = normalizeExtension(extensionDraft);
    if (!normalizedExtension) {
      setExtensionsMessage({
        type: 'error',
        text: '请输入有效的文件后缀，例如 .pdf',
      });
      return;
    }

    if (/\s/.test(normalizedExtension) || normalizedExtension.length < 2) {
      setExtensionsMessage({
        type: 'error',
        text: '文件后缀格式不正确',
      });
      return;
    }

    setAllowedExtensions((previous) =>
      Array.from(new Set([...previous, normalizedExtension])).sort()
    );
    setExtensionDraft('');
    setExtensionsMessage(null);
  };

  const handleDeleteExtension = (extension) => {
    setAllowedExtensions((previous) => previous.filter((item) => item !== extension));
    setExtensionsMessage(null);
  };

  const handleSaveExtensions = async () => {
    if (!canManageExtensions) return;

    if (allowedExtensions.length === 0) {
      setExtensionsMessage({
        type: 'error',
        text: '至少保留一个允许上传的后缀',
      });
      return;
    }

    const changeReason = window.prompt('请输入本次上传后缀配置变更原因');
    if (changeReason === null) return;

    const trimmedReason = String(changeReason || '').trim();
    if (!trimmedReason) {
      setExtensionsMessage({
        type: 'error',
        text: '变更原因不能为空',
      });
      return;
    }

    setSavingExtensions(true);
    setExtensionsMessage(null);

    try {
      const payload = await knowledgeUploadApi.updateAllowedExtensions(
        allowedExtensions,
        trimmedReason
      );
      const nextExtensions = payload.allowedExtensions
        .map(normalizeExtension)
        .filter(Boolean);

      setAllowedExtensions(Array.from(new Set(nextExtensions)).sort());
      setExtensionsMessage({
        type: 'success',
        text: '文件后缀配置已保存并记录变更原因，后续上传立即生效',
      });
    } catch (requestError) {
      setExtensionsMessage({
        type: 'error',
        text: mapUserFacingErrorMessage(requestError?.message, '保存文件后缀配置失败'),
      });
    } finally {
      setSavingExtensions(false);
    }
  };

  return {
    allowedExtensions,
    loadingExtensions,
    savingExtensions,
    extensionDraft,
    extensionsMessage,
    acceptAttr,
    extensionSet,
    setExtensionDraft,
    handleAddExtension,
    handleDeleteExtension,
    handleSaveExtensions,
  };
}
