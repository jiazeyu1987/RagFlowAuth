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
import PatentSourceSummaryPanel from '../features/patentDownload/components/PatentSourceSummaryPanel';
import PatentResultList from '../features/patentDownload/components/PatentResultList';
import usePatentDownloadPage, {
  isSessionActive,
} from '../features/patentDownload/usePatentDownloadPage';
import {
  PATENT_BOX_STYLE,
  PATENT_LOCAL_KB_REF,
  PATENT_SOURCE_LABEL_MAP,
} from '../features/patentDownload/patentDownloadPageUtils';
import { DocumentPreviewModal } from '../shared/documents/preview/DocumentPreviewModal';
import { useAuth } from '../hooks/useAuth';

export default function PatentDownload() {
  const navigate = useNavigate();
  const { canDownload } = useAuth();
  const canDownloadFiles = typeof canDownload === 'function' ? !!canDownload() : false;
  const {
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
          Back To Tools
        </button>
        <div style={{ color: '#6b7280', fontSize: '0.88rem' }}>
          Target KB: <span style={{ color: '#111827', fontWeight: 800 }}>{PATENT_LOCAL_KB_REF}</span>
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
            boxStyle={PATENT_BOX_STYLE}
            title="Keyword Settings"
            keywordLabel="Keywords (comma/semicolon/newline separated)"
            keywordText={keywordText}
            onKeywordChange={setKeywordText}
            placeholder={'3D printer\n导板'}
            useAnd={useAnd}
            onUseAndChange={setUseAnd}
            useAndId="patent-use-and"
            useAndLabel="Use AND (unchecked means OR)"
            parsedTitle="Parsed Keywords"
            parsedKeywords={parsedKeywords}
            emptyParsedText="None"
          />

          <DownloadSourceConfigCard
            boxStyle={PATENT_BOX_STYLE}
            title="Patent Source Settings"
            sourceLabelMap={PATENT_SOURCE_LABEL_MAP}
            sources={sources}
            onUpdateSource={updateSource}
            clampLimit={clampLimit}
            autoAnalyze={autoAnalyze}
            onAutoAnalyzeChange={setAutoAnalyze}
            onRunDownload={runDownload}
            loading={loading}
            autoAnalyzeLabel="Auto Analyze"
            runText="Run Download"
            runLoadingText="Running..."
            limitLabel="Limit"
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
            currentTabText="Current Results"
            historyTabText="History"
            stopText="Stop Download"
            stopBusyText="Stopping..."
            addAllText="Add All To KB"
            addAllBusyText="Adding..."
            removeAllText="Delete All"
          />

          {resultTab === 'current' ? (
            !items.length ? (
              <div style={{ color: '#9ca3af', fontSize: '0.9rem' }}>
                {sessionStatus === 'running'
                  ? 'Downloading, results will stream in...'
                  : 'No current download results'}
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
            <div style={{ display: 'grid', gridTemplateColumns: '280px minmax(420px, 1fr)', gap: '10px' }}>
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
                title="History Keywords"
                refreshText="Refresh"
                loadingText="Loading..."
                emptyText="No history keywords"
                addText="Add to KB"
                addingText="Adding..."
                deleteText="Delete"
                deletingText="Deleting..."
              />
              <DownloadHistoryDetailPanel
                error={historyError}
                loading={historyItemsLoading}
                loadingText="Loading patent history..."
                payload={historyPayload}
                itemLabel="patents"
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
      />
    </div>
  );
}
