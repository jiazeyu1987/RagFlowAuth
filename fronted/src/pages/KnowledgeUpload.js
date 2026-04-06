import React from 'react';

import SelectedFilesList from '../features/knowledge/upload/components/SelectedFilesList';
import UploadDropzone from '../features/knowledge/upload/components/UploadDropzone';
import UploadExtensionsPanel from '../features/knowledge/upload/components/UploadExtensionsPanel';
import {
  uploadPanelStyle,
} from '../features/knowledge/upload/constants';
import useKnowledgeUploadPage from '../features/knowledge/upload/useKnowledgeUploadPage';

const KnowledgeUpload = () => {
  const {
    canManageExtensions,
    isMobile,
    selectedFiles,
    kbId,
    kbSearchKeyword,
    loadingDatasets,
    uploading,
    uploadProgress,
    error,
    success,
    dragActive,
    allowedExtensions,
    loadingExtensions,
    savingExtensions,
    extensionDraft,
    extensionsMessage,
    acceptAttr,
    datasetOptions,
    filteredDatasetOptions,
    setKbId,
    setKbSearchKeyword,
    setExtensionDraft,
    handleUpload,
    handleFileSelect,
    handleFolderSelect,
    handleDrop,
    handleDragOver,
    handleDragLeave,
    clearSelectedFiles,
    removeFile,
    handleAddExtension,
    handleDeleteExtension,
    handleSaveExtensions,
  } = useKnowledgeUploadPage();

  return (
    <div data-testid="knowledge-upload-page">
      <h2 style={{ marginBottom: 24 }}>上传知识库文档</h2>

      <style>{'[data-testid="knowledge-upload-page"] > h2:first-of-type { display: none; }'}</style>

      {error ? (
        <div
          data-testid="upload-error"
          style={{
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            padding: '12px 16px',
            borderRadius: 4,
            marginBottom: 20,
          }}
        >
          {error}
        </div>
      ) : null}

      {success ? (
        <div
          data-testid="upload-success"
          style={{
            backgroundColor: '#d1fae5',
            color: '#065f46',
            padding: '12px 16px',
            borderRadius: 4,
            marginBottom: 20,
          }}
        >
          {success}
        </div>
      ) : null}

      <div
        style={{
          ...uploadPanelStyle,
          maxWidth: '100%',
          padding: isMobile ? 14 : uploadPanelStyle.padding,
        }}
      >
        <form
          onSubmit={handleUpload}
          style={{
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : 'minmax(0, 1.2fr) minmax(320px, 0.9fr)',
            columnGap: 24,
            alignItems: 'start',
          }}
        >
          <div
            style={{
              marginBottom: 24,
              gridColumn: isMobile ? '1' : '2',
              gridRow: isMobile ? 'auto' : '1',
            }}
          >
            <label
              htmlFor="upload-kb-search"
              style={{ display: 'block', marginBottom: 8, fontWeight: 500, color: '#374151' }}
            >
              知识库
            </label>
            <input
              id="upload-kb-search"
              type="text"
              value={kbSearchKeyword}
              onChange={(event) => setKbSearchKeyword(event.target.value)}
              data-testid="upload-kb-search"
              placeholder="输入知识库名称进行模糊匹配"
              style={{
                width: '100%',
                padding: 10,
                border: '1px solid #d1d5db',
                borderRadius: 4,
                fontSize: '0.95rem',
                boxSizing: 'border-box',
                marginBottom: 8,
              }}
            />
            {!loadingDatasets ? (
              <div style={{ marginBottom: 8, fontSize: '0.85rem', color: '#6b7280' }}>
                {`匹配 ${filteredDatasetOptions.length} / ${datasetOptions.length} 个知识库`}
              </div>
            ) : null}
            <select
              value={!loadingDatasets && filteredDatasetOptions.length === 0 ? '' : kbId}
              onChange={(event) => setKbId(event.target.value)}
              disabled={loadingDatasets || filteredDatasetOptions.length === 0}
              data-testid="upload-kb-select"
              style={{
                width: '100%',
                padding: 10,
                border: '1px solid #d1d5db',
                borderRadius: 4,
                fontSize: '1rem',
                boxSizing: 'border-box',
                backgroundColor: loadingDatasets ? '#f3f4f6' : 'white',
              }}
            >
              {loadingDatasets ? (
                <option>加载知识库中...</option>
              ) : filteredDatasetOptions.length > 0 ? (
                filteredDatasetOptions.map((option) => (
                  <option key={option.key} value={option.value}>
                    {option.label}
                  </option>
                ))
              ) : datasetOptions.length > 0 ? (
                <option value="">没有匹配到知识库，请调整搜索关键词</option>
              ) : (
                <option value="">No available knowledge base</option>
              )}
            </select>
          </div>

          <div style={{ gridColumn: isMobile ? '1' : '2', gridRow: isMobile ? 'auto' : '2' }}>
            <UploadExtensionsPanel
              loadingExtensions={loadingExtensions}
              acceptAttr={acceptAttr}
              allowedExtensions={allowedExtensions}
              canManageExtensions={canManageExtensions}
              extensionDraft={extensionDraft}
              onExtensionDraftChange={setExtensionDraft}
              onAddExtension={handleAddExtension}
              onDeleteExtension={handleDeleteExtension}
              onSaveExtensions={handleSaveExtensions}
              savingExtensions={savingExtensions}
              extensionsMessage={extensionsMessage}
            />
          </div>

          <div style={{ gridColumn: '1', gridRow: isMobile ? 'auto' : '1' }}>
            <UploadDropzone
              uploading={uploading}
              dragActive={dragActive}
              selectedFilesLength={selectedFiles.length}
              uploadProgress={uploadProgress}
              acceptAttr={acceptAttr}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onFileSelect={handleFileSelect}
              onFolderSelect={handleFolderSelect}
            />
          </div>

          <div style={{ gridColumn: '1', gridRow: isMobile ? 'auto' : '2' }}>
            <SelectedFilesList
              selectedFiles={selectedFiles}
              uploading={uploading}
              onClear={clearSelectedFiles}
              onRemove={removeFile}
            />

            <div style={{ marginTop: 8, fontSize: '0.85rem', color: '#6b7280', lineHeight: 1.6 }}>
              {`支持后缀：${acceptAttr}（文件夹上传会递归处理）`}
            </div>

            <button
              type="submit"
              disabled={
                selectedFiles.length === 0 ||
                !kbId ||
                uploading ||
                loadingExtensions ||
                allowedExtensions.length === 0
              }
              data-testid="upload-submit"
              style={{
                width: '100%',
                marginTop: 12,
                padding: 12,
                backgroundColor:
                  selectedFiles.length === 0 ||
                  !kbId ||
                  uploading ||
                  loadingExtensions ||
                  allowedExtensions.length === 0
                    ? '#9ca3af'
                    : '#3b82f6',
                color: 'white',
                border: 'none',
                borderRadius: 4,
                fontSize: '1rem',
                fontWeight: 500,
                cursor:
                  selectedFiles.length === 0 ||
                  !kbId ||
                  uploading ||
                  loadingExtensions ||
                  allowedExtensions.length === 0
                    ? 'not-allowed'
                    : 'pointer',
              }}
            >
              {uploading
                ? '上传中...'
                : `上传文档${selectedFiles.length > 0 ? `（${selectedFiles.length}）` : ''}`}
            </button>
          </div>
        </form>

        <div
          style={{
            marginTop: 24,
            padding: isMobile ? 14 : 16,
            backgroundColor: '#f9fafb',
            borderRadius: 4,
            fontSize: '0.9rem',
            color: '#6b7280',
            lineHeight: 1.6,
          }}
        >
          <div style={{ marginBottom: 8, fontWeight: 500, color: '#374151' }}>上传流程</div>
          <ol style={{ margin: 0, paddingLeft: 20 }}>
            <li>选择知识库并上传文件</li>
            <li>文档进入“待审核”状态</li>
            <li>审核通过后自动同步到知识库</li>
          </ol>
        </div>
      </div>
    </div>
  );
};

export default KnowledgeUpload;
