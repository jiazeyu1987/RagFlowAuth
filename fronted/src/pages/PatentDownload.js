import React from 'react';

import { clampLimit } from '../features/download/downloadPageUtils';
import DownloadHistorySidebar from '../features/download/components/DownloadHistorySidebar';
import DownloadHistoryDetailPanel from '../features/download/components/DownloadHistoryDetailPanel';
import DownloadResultToolbar from '../features/download/components/DownloadResultToolbar';
import {
  DownloadKeywordConfigCard,
  DownloadSourceConfigCard,
} from '../features/download/components/DownloadConfigCards';
import { documentsApi } from '../features/documents/api';
import PatentResultList from '../features/patentDownload/components/PatentResultList';
import PatentSourceSummaryPanel from '../features/patentDownload/components/PatentSourceSummaryPanel';
import usePatentDownloadPage, { isSessionActive } from '../features/patentDownload/usePatentDownloadPage';
import {
  PATENT_BOX_STYLE,
  PATENT_LOCAL_KB_REF,
  PATENT_SOURCE_LABEL_MAP,
} from '../features/patentDownload/patentDownloadPageUtils';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';

export default function PatentDownload() {
  const {
    isMobile,
    canDownloadFiles,
    handleBackToTools,
    keywordText,
    useAnd,
    autoAnalyze,
    sources,
    sourceStats,
    loading,
    stopping,
    addingAll,
    deletingSession,
    error,
    info,
    resultTab,
    sessionId,
    sessionStatus,
    items,
    parsedKeywords,
    frontendLogs,
    addingItemId,
    deletingItemId,
    previewOpen,
    previewTarget,
    historyKeywords,
    historyLoading,
    historyError,
    selectedHistoryKey,
    historyPayload,
    historyItems,
    historyItemsLoading,
    deletingHistoryKey,
    addingHistoryKey,
    setKeywordText,
    setUseAnd,
    setAutoAnalyze,
    setResultTab,
    setPreviewOpen,
    setSelectedHistoryKey,
    updateSource,
    runDownload,
    stopDownload,
    addAll,
    removeSession,
    addOne,
    deleteOne,
    openPreview,
    deleteHistoryKeyword,
    addHistoryKeywordToKb,
    refreshHistoryPanel,
  } = usePatentDownloadPage();

  return (
    <div style={{ display: 'grid', gap: '12px' }} data-testid="patent-download-page">
      <div
        style={{
          display: 'flex',
          alignItems: isMobile ? 'stretch' : 'center',
          justifyContent: 'space-between',
          gap: '12px',
          flexDirection: isMobile ? 'column' : 'row',
        }}
      >
        <button
          type="button"
          data-testid="patent-download-back"
          onClick={handleBackToTools}
          style={{
            padding: '8px 12px',
            borderRadius: '10px',
            border: '1px solid #e5e7eb',
            background: '#fff',
            cursor: 'pointer',
            fontWeight: 700,
            width: isMobile ? '100%' : 'auto',
          }}
        >
          返回工具页
        </button>
        <div
          style={{
            color: '#6b7280',
            fontSize: '0.88rem',
            width: isMobile ? '100%' : 'auto',
            wordBreak: 'break-word',
          }}
        >
          目标知识库：<span style={{ color: '#111827', fontWeight: 800 }}>{PATENT_LOCAL_KB_REF}</span>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isMobile ? '1fr' : 'minmax(340px, 1fr) minmax(680px, 2fr)',
          gap: '12px',
          alignItems: 'start',
        }}
      >
        <div style={{ display: 'grid', gap: '12px' }}>
          <DownloadKeywordConfigCard
            boxStyle={PATENT_BOX_STYLE}
            title="关键词设置"
            keywordLabel="关键词（支持逗号 / 分号 / 换行分隔）"
            keywordText={keywordText}
            onKeywordChange={setKeywordText}
            placeholder={'3D 打印机\n导板'}
            useAnd={useAnd}
            onUseAndChange={setUseAnd}
            useAndId="patent-use-and"
            useAndLabel="使用 AND（不勾选则为 OR）"
            parsedTitle="解析后的关键词"
            parsedKeywords={parsedKeywords}
            emptyParsedText="暂无"
          />

          <DownloadSourceConfigCard
            boxStyle={PATENT_BOX_STYLE}
            title="专利源设置"
            sourceLabelMap={PATENT_SOURCE_LABEL_MAP}
            sources={sources}
            onUpdateSource={updateSource}
            clampLimit={clampLimit}
            autoAnalyze={autoAnalyze}
            onAutoAnalyzeChange={setAutoAnalyze}
            onRunDownload={runDownload}
            loading={loading}
            autoAnalyzeLabel="自动解析"
            runText="开始下载"
            runLoadingText="下载中..."
            limitLabel="数量上限"
          >
            <PatentSourceSummaryPanel
              sourceStats={sourceStats}
              error={error}
              info={info}
              frontendLogs={frontendLogs}
              sourceLabelMap={PATENT_SOURCE_LABEL_MAP}
            />
          </DownloadSourceConfigCard>
        </div>

        <section style={PATENT_BOX_STYLE}>
          <DownloadResultToolbar
            resultTab={resultTab}
            onChangeTab={setResultTab}
            showActions={resultTab === 'current'}
            onStop={stopDownload}
            onAddAll={addAll}
            onRemoveAll={removeSession}
            stopDisabled={!sessionId || !isSessionActive(sessionStatus) || stopping}
            addAllDisabled={!sessionId || addingAll}
            removeAllDisabled={!sessionId || deletingSession}
            stopBusy={stopping}
            addAllBusy={addingAll}
            currentTabText="当前结果"
            historyTabText="历史记录"
            stopText="停止下载"
            stopBusyText="停止中..."
            addAllText="全部加入知识库"
            addAllBusyText="加入中..."
            removeAllText="删除全部"
          />

          {resultTab === 'current' ? (
            !items.length ? (
              <div style={{ color: '#9ca3af', fontSize: '0.9rem' }}>
                {sessionStatus === 'running' ? '正在下载，结果会陆续出现...' : '暂无当前下载结果'}
              </div>
            ) : (
              <PatentResultList
                items={items}
                sessionId={sessionId}
                addingItemId={addingItemId}
                deletingItemId={deletingItemId}
                onView={openPreview}
                onAdd={addOne}
                onDelete={deleteOne}
              />
            )
          ) : (
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: isMobile ? '1fr' : '280px minmax(420px, 1fr)',
                gap: '10px',
              }}
            >
              <DownloadHistorySidebar
                rows={historyKeywords}
                selectedKey={selectedHistoryKey}
                addingKey={addingHistoryKey}
                deletingKey={deletingHistoryKey}
                loading={historyLoading}
                loadingItems={historyItemsLoading}
                onRefresh={refreshHistoryPanel}
                onSelectKey={(key) => setSelectedHistoryKey(key)}
                onAdd={addHistoryKeywordToKb}
                onDelete={deleteHistoryKeyword}
                title="历史关键词"
                refreshText="刷新"
                loadingText="加载中..."
                emptyText="暂无历史关键词"
                addText="加入知识库"
                addingText="加入中..."
                deleteText="删除"
                deletingText="删除中..."
              />
              <DownloadHistoryDetailPanel
                error={historyError}
                loading={historyItemsLoading}
                loadingText="正在加载专利历史..."
                payload={historyPayload}
                itemLabel="专利"
              >
                <PatentResultList
                  items={historyItems}
                  sessionId={sessionId}
                  addingItemId={addingItemId}
                  deletingItemId={deletingItemId}
                  onView={openPreview}
                  onAdd={addOne}
                  onDelete={deleteOne}
                />
              </DownloadHistoryDetailPanel>
            </div>
          )}
        </section>
      </div>

      <DocumentPreviewModal
        open={previewOpen}
        onClose={() => setPreviewOpen(false)}
        target={previewTarget}
        canDownloadFiles={canDownloadFiles}
        documentApi={documentsApi}
      />
    </div>
  );
}
