import React from 'react';
import QualitySystemUserMultiSelect from '../features/qualitySystemConfig/components/QualitySystemUserMultiSelect';
import useQualitySystemConfigPage from '../features/qualitySystemConfig/useQualitySystemConfigPage';

const TEXT = {
  title: '\u4f53\u7cfb\u914d\u7f6e',
  summary:
    '\u5728\u8fd9\u91cc\u7ba1\u7406\u5c97\u4f4d\u5bf9\u5e94\u5458\u5de5\u4e0e\u6587\u4ef6\u5c0f\u7c7b\uff0c\u6240\u6709\u53d8\u66f4\u90fd\u4f1a\u5199\u5165\u65e5\u5fd7\u5ba1\u8ba1\u3002',
  positionsTab: '\u5c97\u4f4d\u5206\u914d',
  categoriesTab: '\u6587\u4ef6\u5c0f\u7c7b',
  positionsEmpty: '\u6682\u65e0\u53ef\u914d\u7f6e\u5c97\u4f4d\u3002',
  categoriesEmpty: '\u6682\u65e0\u6587\u4ef6\u5c0f\u7c7b\u3002',
  addCategory: '\u65b0\u589e\u6587\u4ef6\u5c0f\u7c7b',
  saveAssignments: '\u4fdd\u5b58\u5206\u914d',
  removeCategory: '\u51cf\u5c11',
  sourceSignoff: '\u5ba1\u6838\u4f1a\u7b7e',
  sourceCompiler: '\u7f16\u5236',
  sourceApprover: '\u6279\u51c6',
};

const pageStyle = {
  maxWidth: '1280px',
  display: 'grid',
  gap: '16px',
};

const cardStyle = {
  background: '#ffffff',
  border: '1px solid #dbe2ea',
  borderRadius: '16px',
  padding: '18px',
  boxShadow: '0 10px 30px rgba(15, 23, 42, 0.06)',
};

const tabButtonStyle = (active) => ({
  padding: '10px 14px',
  borderRadius: '10px',
  border: active ? '1px solid #0f766e' : '1px solid #cbd5e1',
  background: active ? '#0f766e' : '#ffffff',
  color: active ? '#ffffff' : '#0f172a',
  cursor: 'pointer',
  fontWeight: 700,
});

const pillStyle = (background, color) => ({
  display: 'inline-flex',
  alignItems: 'center',
  gap: '6px',
  borderRadius: '999px',
  padding: '4px 10px',
  background,
  color,
  fontSize: '0.8rem',
  fontWeight: 700,
});

const buildSourceTags = (position) => {
  const tags = [];
  if (position?.in_signoff) tags.push(TEXT.sourceSignoff);
  if (position?.in_compiler) tags.push(TEXT.sourceCompiler);
  if (position?.in_approver) tags.push(TEXT.sourceApprover);
  return tags;
};

export default function QualitySystemConfig() {
  const {
    loading,
    error,
    notice,
    activeTab,
    tabs,
    positions,
    fileCategories,
    categoryName,
    categorySubmitting,
    deactivatingCategoryId,
    savingAssignments,
    setActiveTab,
    setCategoryName,
    updatePositionDraft,
    saveAssignments,
    createCategory,
    deactivateCategory,
    searchUsers,
  } = useQualitySystemConfigPage();

  const handleSaveAssignments = async (positionId) => {
    const changeReason = window.prompt('Please enter the reason for this assignment change.');
    if (changeReason === null) return;
    await saveAssignments(positionId, changeReason);
  };

  const handleCreateCategory = async () => {
    const changeReason = window.prompt('Please enter the reason for this file category change.');
    if (changeReason === null) return;
    await createCategory(changeReason);
  };

  const handleDeactivateCategory = async (category) => {
    const confirmed = window.confirm(`Remove "${String(category?.name || '')}" from the active list?`);
    if (!confirmed) return;
    const changeReason = window.prompt('Please enter the reason for removing this file category.');
    if (changeReason === null) return;
    await deactivateCategory(category.id, changeReason);
  };

  if (loading) {
    return <div style={{ padding: '12px' }}>Loading quality system configuration...</div>;
  }

  return (
    <div style={pageStyle} data-testid="quality-system-config-page">
      <section
        style={{
          ...cardStyle,
          background: 'linear-gradient(135deg, #f0fdfa 0%, #ecfeff 55%, #f8fafc 100%)',
          borderColor: '#99f6e4',
        }}
      >
        <h2 style={{ margin: 0, color: '#0f172a' }}>{TEXT.title}</h2>
        <p style={{ margin: '10px 0 0', color: '#334155', maxWidth: '760px', lineHeight: 1.6 }}>
          {TEXT.summary}
        </p>
      </section>

      {error ? (
        <div
          data-testid="quality-system-config-error"
          style={{
            ...cardStyle,
            borderColor: '#fecaca',
            background: '#fef2f2',
            color: '#991b1b',
          }}
        >
          {error}
        </div>
      ) : null}

      {notice ? (
        <div
          data-testid="quality-system-config-notice"
          style={{
            ...cardStyle,
            borderColor: '#bbf7d0',
            background: '#f0fdf4',
            color: '#166534',
          }}
        >
          {notice}
        </div>
      ) : null}

      <section style={cardStyle}>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          <button
            type="button"
            onClick={() => setActiveTab(tabs.positions)}
            style={tabButtonStyle(activeTab === tabs.positions)}
            data-testid="quality-system-config-tab-positions"
          >
            {TEXT.positionsTab}
          </button>
          <button
            type="button"
            onClick={() => setActiveTab(tabs.categories)}
            style={tabButtonStyle(activeTab === tabs.categories)}
            data-testid="quality-system-config-tab-categories"
          >
            {TEXT.categoriesTab}
          </button>
        </div>
      </section>

      {activeTab === tabs.positions ? (
        <section style={cardStyle} data-testid="quality-system-config-positions">
          {positions.length === 0 ? (
            <div style={{ color: '#64748b' }}>{TEXT.positionsEmpty}</div>
          ) : (
            <div style={{ display: 'grid', gap: '14px' }}>
              {positions.map((position) => (
                <article
                  key={position.id}
                  style={{
                    border: '1px solid #dbe2ea',
                    borderRadius: '14px',
                    padding: '16px',
                    display: 'grid',
                    gap: '12px',
                  }}
                  data-testid={`quality-system-config-position-${position.id}`}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', flexWrap: 'wrap' }}>
                    <div>
                      <div style={{ fontWeight: 700, color: '#0f172a' }}>{position.name}</div>
                      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' }}>
                        {buildSourceTags(position).map((tag) => (
                          <span
                            key={`${position.id}-${tag}`}
                            style={pillStyle('#f1f5f9', '#475569')}
                          >
                            {tag}
                          </span>
                        ))}
                      </div>
                    </div>
                    <button
                      type="button"
                      onClick={() => handleSaveAssignments(position.id)}
                      disabled={!position.is_dirty || !!savingAssignments[position.id]}
                      style={{
                        padding: '10px 14px',
                        borderRadius: '10px',
                        border: '1px solid #0f766e',
                        background: !position.is_dirty || !!savingAssignments[position.id] ? '#9ca3af' : '#0f766e',
                        color: '#ffffff',
                        cursor: !position.is_dirty || !!savingAssignments[position.id] ? 'not-allowed' : 'pointer',
                        fontWeight: 700,
                      }}
                      data-testid={`quality-system-config-position-save-${position.id}`}
                    >
                      {savingAssignments[position.id] ? 'Saving...' : TEXT.saveAssignments}
                    </button>
                  </div>

                  <QualitySystemUserMultiSelect
                    selectedUsers={position.draft_assigned_users}
                    onChange={(users) => updatePositionDraft(position.id, users)}
                    onSearch={searchUsers}
                    testIdPrefix={`quality-system-config-position-users-${position.id}`}
                  />
                </article>
              ))}
            </div>
          )}
        </section>
      ) : null}

      {activeTab === tabs.categories ? (
        <section style={cardStyle} data-testid="quality-system-config-categories">
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'minmax(0, 1fr) auto',
              gap: '12px',
              marginBottom: '16px',
            }}
          >
            <input
              value={categoryName}
              onChange={(event) => setCategoryName(event.target.value)}
              placeholder="Add a new file category"
              data-testid="quality-system-config-category-input"
              style={{
                width: '100%',
                padding: '10px 12px',
                borderRadius: '10px',
                border: '1px solid #cbd5e1',
                boxSizing: 'border-box',
              }}
            />
            <button
              type="button"
              onClick={handleCreateCategory}
              disabled={categorySubmitting}
              data-testid="quality-system-config-category-add"
              style={{
                padding: '10px 14px',
                borderRadius: '10px',
                border: '1px solid #0f766e',
                background: categorySubmitting ? '#9ca3af' : '#0f766e',
                color: '#ffffff',
                cursor: categorySubmitting ? 'not-allowed' : 'pointer',
                fontWeight: 700,
              }}
            >
              {categorySubmitting ? 'Saving...' : TEXT.addCategory}
            </button>
          </div>

          {fileCategories.length === 0 ? (
            <div style={{ color: '#64748b' }}>{TEXT.categoriesEmpty}</div>
          ) : (
            <div style={{ display: 'grid', gap: '10px' }}>
              {fileCategories.map((category) => (
                <div
                  key={category.id}
                  style={{
                    border: '1px solid #dbe2ea',
                    borderRadius: '12px',
                    padding: '14px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: '12px',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                  }}
                  data-testid={`quality-system-config-category-${category.id}`}
                >
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 700, color: '#0f172a' }}>{category.name}</span>
                    {category.seeded_from_json ? (
                      <span style={pillStyle('#ecfeff', '#155e75')}>JSON seed</span>
                    ) : (
                      <span style={pillStyle('#fef3c7', '#92400e')}>Custom</span>
                    )}
                  </div>
                  <button
                    type="button"
                    onClick={() => handleDeactivateCategory(category)}
                    disabled={deactivatingCategoryId === category.id}
                    style={{
                      padding: '8px 12px',
                      borderRadius: '10px',
                      border: '1px solid #ef4444',
                      background: deactivatingCategoryId === category.id ? '#9ca3af' : '#ffffff',
                      color: deactivatingCategoryId === category.id ? '#ffffff' : '#b91c1c',
                      cursor: deactivatingCategoryId === category.id ? 'not-allowed' : 'pointer',
                      fontWeight: 700,
                    }}
                    data-testid={`quality-system-config-category-remove-${category.id}`}
                  >
                    {deactivatingCategoryId === category.id ? 'Removing...' : TEXT.removeCategory}
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
      ) : null}
    </div>
  );
}
