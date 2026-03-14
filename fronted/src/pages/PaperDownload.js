import React from 'react';
import { useNavigate } from 'react-router-dom';
import { clampLimit } from '../features/download/downloadPageUtils';
import DownloadHistorySidebar from '../features/download/components/DownloadHistorySidebar';
import DownloadHistoryDetailPanel from '../features/download/components/DownloadHistoryDetailPanel';
import DownloadResultToolbar from '../features/download/components/DownloadResultToolbar';
import {
  DownloadKeywordConfigCard,
  DownloadSourceConfigCard,
} from '../features/download/components/DownloadConfigCards';
import PaperResultList from '../features/paperDownload/components/PaperResultList';
import PaperSourceSummaryPanel from '../features/paperDownload/components/PaperSourceSummaryPanel';
import usePaperDownloadPage, {
  isSessionActive,
} from '../features/paperDownload/usePaperDownloadPage';
import {
  PAPER_BOX_STYLE,
  PAPER_LOCAL_KB_REF,
  PAPER_SOURCE_LABEL_MAP,
} from '../features/paperDownload/paperDownloadPageUtils';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';
import { useAuth } from '../hooks/useAuth';

export default function PaperDownload() {
  const navigate = useNavigate();
  const { canDownload } = useAuth();
  const canDownloadFiles = typeof canDownload === 'function' ? !!canDownload() : false;
  const {
    keywordText,
    useAnd,
    autoAnalyze,
    sources,
    sourceErrors,
    sourceStats,
    loading,
    stopping,
    addingAll,
    deletingSession,
    addingItemId,
    deletingItemId,
    resultTab,
    deletingHistoryKey,
    addingHistoryKey,
    previewOpen,
    previewTarget,
    error,
    info,
    parsedKeywords,
    sessionId,
    sessionStatus,
    items,
    historyKeywords,
    historyLoading,
    historyError,
    selectedHistoryKey,
    historyPayload,
    historyItems,
    historyItemsLoading,
    setKeywordText,
    setUseAnd,
    setAutoAnalyze,
    setResultTab,
    setPreviewOpen,
    setSelectedHistoryKey,
    updateSource,
    runDownload,
    stopDownload,
    openPreview,
    addOne,
    deleteOne,
    addAll,
    removeSession,
    deleteHistoryKeyword,
    addHistoryKeywordToKb,
    refreshHistoryPanel,
  } = usePaperDownloadPage();

  return (
    <div style={{ display: 'grid', gap: '12px' }} data-testid="paper-download-page">
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '12px',
        }}
      >
        <button
          type="button"
          onClick={() => navigate('/tools')}
          style={{
            padding: '8px 12px',
            borderRadius: '10px',
            border: '1px solid #e5e7eb',
            background: '#fff',
            cursor: 'pointer',
            fontWeight: 700,
          }}
        >
          返回实用工具
        </button>
        <div style={{ color: '#6b7280', fontSize: '0.88rem' }}>
          目标知识库：<span style={{ color: '#111827', fontWeight: 800 }}>{PAPER_LOCAL_KB_REF}</span>
        </div>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(340px, 1fr) minmax(680px, 2fr)',
          gap: '12px',
          alignItems: 'start',
        }}
      >
        <div style={{ display: 'grid', gap: '12px' }}>
          <DownloadKeywordConfigCard
            boxStyle={PAPER_BOX_STYLE}
            title="关键词设置"
            keywordLabel="关键词（可用逗号/分号/换行分隔）"
            keywordText={keywordText}
            onKeywordChange={setKeywordText}
            placeholder={'3D打印\n导板'}
            useAnd={useAnd}
            onUseAndChange={setUseAnd}
            useAndId="paper-use-and"
            useAndLabel="使用“并且”逻辑（不勾选则使用“或者”）"
            parsedTitle="解析后的关键词"
            parsedKeywords={parsedKeywords}
            emptyParsedText="无"
          />

          <DownloadSourceConfigCard
            boxStyle={PAPER_BOX_STYLE}
            title="论文来源设置"
            sourceLabelMap={PAPER_SOURCE_LABEL_MAP}
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
            <PaperSourceSummaryPanel
              sourceStats={sourceStats}
              sourceErrors={sourceErrors}
              error={error}
              info={info}
              sourceLabelMap={PAPER_SOURCE_LABEL_MAP}
            />
          </DownloadSourceConfigCard>
        </div>

        <section style={PAPER_BOX_STYLE}>
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
            addAllBusyText="处理中..."
            removeAllText="删除全部"
          />

          {resultTab === 'current' ? (
            !items.length ? (
              <div style={{ color: '#9ca3af', fontSize: '0.9rem' }}>
                {sessionStatus === 'running'
                  ? '下载进行中，结果会持续更新...'
                  : '当前暂无下载结果'}
              </div>
            ) : (
              <PaperResultList
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
                gridTemplateColumns: '280px minmax(420px, 1fr)',
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
                addingText="处理中..."
                deleteText="删除"
                deletingText="删除中..."
              />
              <DownloadHistoryDetailPanel
                error={historyError}
                loading={historyItemsLoading}
                loadingText="正在加载论文历史..."
                payload={historyPayload}
                itemLabel="论文"
              >
                <PaperResultList
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
      />
    </div>
  );
}
