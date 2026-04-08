import React from 'react';

import {
  SEARCH_RESULT_LIMIT,
  actionLabel,
  buildDingtalkRebuildResultText,
  formatDateTime,
  reasonLabel,
  searchTypeLabel,
  toSearchResultTestId,
} from '../helpers';
import { panelStyle } from '../pageStyles';

function MetricCard({ label, value, meta }) {
  return (
    <div style={{ ...panelStyle, padding: 12 }}>
      <div style={{ color: '#6b7280', fontSize: '0.74rem' }}>{label}</div>
      <div style={{ marginTop: 6, fontSize: '1.45rem', fontWeight: 800 }}>{value}</div>
      {meta ? (
        <div style={{ marginTop: 4, color: '#6b7280', fontSize: '0.74rem' }}>
          {meta}
        </div>
      ) : null}
    </div>
  );
}

export default function OrgOverviewPanel({
  isMobile,
  excelFileInputRef,
  rebuilding,
  searchTerm,
  selectedSearchKey,
  selectedPersonEntry,
  selectedExcelFile,
  recipientMapRebuildSummary,
  personCount,
  companies,
  departments,
  latestOverviewAudit,
  isMissingPersonNodes,
  canTriggerRebuild,
  trimmedSearchTerm,
  totalSearchMatches,
  searchResults,
  handleSearchInputChange,
  handleClearSearch,
  handleSelectSearchResult,
  handleChooseExcelFile,
  handleClearExcelFile,
  handleExcelFileChange,
  handleRebuild,
}) {
  return (
    <div style={{ display: 'grid', gap: 14 }}>
      {isMissingPersonNodes ? (
        <div
          data-testid="org-empty-people-warning"
          style={{
            padding: '12px 14px',
            borderRadius: 10,
            backgroundColor: '#fff7ed',
            border: '1px solid #fdba74',
            color: '#9a3412',
          }}
        >
          <div style={{ fontWeight: 700 }}>当前组织库缺少人员叶子节点</div>
          <div style={{ marginTop: 6, fontSize: '0.82rem', lineHeight: 1.7 }}>
            当前树数据里没有任何 `person` 节点，请先选择组织架构 Excel 文件，再点击下方“从 Excel 重建组织架构”，把员工节点写入当前活动库后再查看个人叶子。
          </div>
        </div>
      ) : null}

      {selectedPersonEntry ? (
        <div
          data-testid="org-selected-person-overview"
          style={{
            padding: '12px 14px',
            borderRadius: 10,
            border: '1px solid #bfdbfe',
            backgroundColor: '#f8fbff',
          }}
        >
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              flexWrap: 'wrap',
            }}
          >
            <div style={{ fontSize: '0.92rem', fontWeight: 700, color: '#111827' }}>
              {selectedPersonEntry.node.name}
            </div>
            {selectedPersonEntry.node.is_department_manager ? (
              <div style={{ fontSize: '0.78rem', fontWeight: 700, color: '#15803d' }}>
                部门主管
              </div>
            ) : null}
          </div>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? '1fr' : 'repeat(2, minmax(0, 1fr))',
              gap: 10,
              marginTop: 10,
            }}
          >
            <div style={{ ...panelStyle, padding: 10 }}>
              <div style={{ color: '#6b7280', fontSize: '0.74rem' }}>员工UserID</div>
              <div style={{ marginTop: 4, color: '#111827', fontSize: '0.84rem', fontWeight: 700 }}>
                {selectedPersonEntry.node.employee_user_id || '-'}
              </div>
            </div>
            <div style={{ ...panelStyle, padding: 10 }}>
              <div style={{ color: '#6b7280', fontSize: '0.74rem' }}>部门主管</div>
              <div
                style={{
                  marginTop: 4,
                  color: selectedPersonEntry.node.is_department_manager ? '#15803d' : '#111827',
                  fontSize: '0.84rem',
                  fontWeight: 700,
                }}
              >
                {selectedPersonEntry.node.department_manager_name || '-'}
              </div>
            </div>
          </div>
        </div>
      ) : null}

      <div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <input
            type="text"
            value={searchTerm}
            onChange={handleSearchInputChange}
            placeholder="搜索公司、部门、人员或员工UserID"
            data-testid="org-search-input"
            style={{
              flex: 1,
              minWidth: 0,
              padding: '10px 12px',
              borderRadius: 10,
              border: '1px solid #cbd5e1',
              fontSize: '0.9rem',
            }}
          />
          <button
            type="button"
            onClick={handleClearSearch}
            data-testid="org-search-clear"
            style={{
              padding: '10px 12px',
              borderRadius: 10,
              border: '1px solid #d1d5db',
              backgroundColor: '#ffffff',
              cursor: 'pointer',
            }}
          >
            清空
          </button>
        </div>

        {trimmedSearchTerm ? (
          <div style={{ display: 'grid', gap: 8, marginTop: 10 }}>
            <div style={{ color: '#64748b', fontSize: '0.82rem' }}>
              搜索结果 {searchResults.length > 0 ? `${searchResults.length} 条` : ''}
              {totalSearchMatches > SEARCH_RESULT_LIMIT ? `，仅显示前 ${SEARCH_RESULT_LIMIT} 条` : ''}
            </div>

            {searchResults.length > 0 ? (
              <div style={{ display: 'grid', gap: 6, maxHeight: 240, overflowY: 'auto' }}>
                {searchResults.map((entry) => (
                  <button
                    key={entry.key}
                    type="button"
                    data-testid={toSearchResultTestId(entry)}
                    onClick={() => handleSelectSearchResult(entry)}
                    style={{
                      textAlign: 'left',
                      border: `1px solid ${selectedSearchKey === entry.key ? '#60a5fa' : '#e5e7eb'}`,
                      backgroundColor: selectedSearchKey === entry.key ? '#eff6ff' : '#ffffff',
                      borderRadius: 10,
                      padding: '9px 10px',
                      cursor: 'pointer',
                    }}
                  >
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '0.74rem', color: '#2563eb', fontWeight: 700 }}>
                        {searchTypeLabel(entry.nodeType)}
                      </span>
                      <span style={{ fontSize: '0.86rem', fontWeight: 700, color: '#111827' }}>
                        {entry.name}
                      </span>
                      {entry.employeeUserId ? (
                        <span style={{ fontSize: '0.76rem', color: '#64748b' }}>
                          员工UserID {entry.employeeUserId}
                        </span>
                      ) : null}
                    </div>
                    <div
                      style={{
                        marginTop: 4,
                        color: '#6b7280',
                        fontSize: '0.76rem',
                        wordBreak: 'break-word',
                      }}
                    >
                      {entry.pathName}
                    </div>
                  </button>
                ))}
              </div>
            ) : (
              <div data-testid="org-search-empty" style={{ color: '#6b7280', fontSize: '0.84rem' }}>
                没有匹配结果，请换个关键词。
              </div>
            )}
          </div>
        ) : null}
      </div>

      <div
        style={{
          ...panelStyle,
          padding: 12,
          display: 'grid',
          gap: 10,
        }}
      >
        <input
          ref={excelFileInputRef}
          type="file"
          accept=".xls,.xlsx,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={handleExcelFileChange}
          data-testid="org-excel-file-input"
          style={{ display: 'none' }}
        />
        <div>
          <div style={{ color: '#111827', fontSize: '0.9rem', fontWeight: 700 }}>组织架构文件</div>
          <div style={{ marginTop: 4, color: '#6b7280', fontSize: '0.78rem' }}>
            请选择 Excel 文件，仅支持 .xls / .xlsx。
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={handleChooseExcelFile}
            disabled={rebuilding}
            data-testid="org-excel-file-trigger"
            style={{
              padding: '10px 12px',
              borderRadius: 10,
              border: '1px solid #d1d5db',
              backgroundColor: '#ffffff',
              color: '#111827',
              cursor: rebuilding ? 'not-allowed' : 'pointer',
              fontWeight: 600,
            }}
          >
            选择组织架构文件
          </button>
          {selectedExcelFile ? (
            <button
              type="button"
              onClick={handleClearExcelFile}
              disabled={rebuilding}
              data-testid="org-excel-file-clear"
              style={{
                padding: '10px 12px',
                borderRadius: 10,
                border: '1px solid #d1d5db',
                backgroundColor: '#ffffff',
                color: '#6b7280',
                cursor: rebuilding ? 'not-allowed' : 'pointer',
              }}
            >
              清除
            </button>
          ) : null}
        </div>
        <div
          data-testid="org-excel-file-name"
          style={{
            padding: '10px 12px',
            borderRadius: 10,
            border: '1px dashed #cbd5e1',
            backgroundColor: selectedExcelFile ? '#f8fbff' : '#f8fafc',
            color: selectedExcelFile ? '#111827' : '#6b7280',
            fontSize: '0.82rem',
            wordBreak: 'break-word',
          }}
        >
          {selectedExcelFile ? selectedExcelFile.name : '未加载组织架构文件'}
        </div>
        <button
          type="button"
          data-testid="org-rebuild-trigger"
          onClick={handleRebuild}
          disabled={!canTriggerRebuild}
          style={{
            width: '100%',
            padding: '11px 14px',
            backgroundColor: canTriggerRebuild ? '#2563eb' : '#cbd5e1',
            color: '#ffffff',
            border: 'none',
            borderRadius: 10,
            cursor: canTriggerRebuild ? 'pointer' : 'not-allowed',
            fontWeight: 700,
          }}
        >
          {rebuilding ? '重建中...' : '从 Excel 重建组织架构'}
        </button>
      </div>

      {recipientMapRebuildSummary ? (
        <div
          data-testid="org-dingtalk-rebuild-summary"
          style={{
            ...panelStyle,
            padding: 12,
            border: '1px solid #bfdbfe',
            backgroundColor: '#f8fbff',
          }}
        >
          <div style={{ fontSize: '0.78rem', color: '#2563eb', fontWeight: 700 }}>
            钉钉 UserID 目录重建结果
          </div>
          <div style={{ marginTop: 6, color: '#111827', fontSize: '0.84rem' }}>
            通道: {recipientMapRebuildSummary.channel_id}
          </div>
          <div style={{ marginTop: 4, color: '#475569', fontSize: '0.82rem', lineHeight: 1.7 }}>
            {buildDingtalkRebuildResultText(recipientMapRebuildSummary)}
          </div>
          {(recipientMapRebuildSummary.invalid_org_users || []).length > 0 ? (
            <div style={{ display: 'grid', gap: 6, marginTop: 10 }}>
              {(recipientMapRebuildSummary.invalid_org_users || []).map((item) => (
                <div
                  key={`${item.employee_user_id}-${item.full_name}`}
                  data-testid={`org-dingtalk-invalid-${item.employee_user_id || item.full_name || 'unknown'}`}
                  style={{
                    padding: '8px 10px',
                    borderRadius: 8,
                    backgroundColor: '#ffffff',
                    border: '1px solid #dbeafe',
                    color: '#334155',
                    fontSize: '0.8rem',
                  }}
                >
                  {(item.full_name || item.employee_user_id || '-') + ' 路 ' + reasonLabel(item.reason)}
                </div>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
          gap: 10,
        }}
      >
        <MetricCard label="公司节点" value={companies.length} />
        <MetricCard label="部门节点" value={departments.length} />
        <MetricCard label="人员节点" value={personCount} />
        <MetricCard
          label="最近组织操作"
          value={latestOverviewAudit ? actionLabel(latestOverviewAudit.action) : '暂无'}
          meta={latestOverviewAudit ? formatDateTime(latestOverviewAudit.created_at_ms) : '-'}
        />
      </div>
    </div>
  );
}
