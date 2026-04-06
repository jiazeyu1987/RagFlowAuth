import React, { useEffect, useRef } from 'react';
import useApprovalConfigPage, {
  buildMemberSearchKey,
  buildUserLabel,
  createUserSearchState,
  specialRoleLabel,
  WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE,
  WORKFLOW_MEMBER_TYPE_USER,
} from '../features/operationApproval/useApprovalConfigPage';

const USER_SEARCH_DELAY_MS = 250;

const cardStyle = {
  background: '#ffffff',
  border: '1px solid #e5e7eb',
  borderRadius: '14px',
  padding: '16px',
};

const buttonStyle = {
  border: '1px solid #d1d5db',
  borderRadius: '10px',
  background: '#ffffff',
  color: '#111827',
  cursor: 'pointer',
  padding: '8px 12px',
};

const inputStyle = {
  padding: '10px 12px',
  border: '1px solid #d1d5db',
  borderRadius: '10px',
  width: '100%',
  background: '#ffffff',
};

const primaryButtonStyle = {
  ...buttonStyle,
  background: '#2563eb',
  borderColor: '#2563eb',
  color: '#ffffff',
};

function UserLookupField({
  searchKey,
  selectedUser,
  searchState,
  onSearchStateChange,
  onInputChange,
  onSelectUser,
  searchUsers,
  testIdPrefix,
}) {
  const blurTimerRef = useRef(null);

  useEffect(
    () => () => {
      if (blurTimerRef.current) {
        window.clearTimeout(blurTimerRef.current);
      }
    },
    []
  );

  useEffect(() => {
    const keyword = String(searchState?.keyword || '').trim();
    if (!searchState?.open) return undefined;
    if (!keyword) {
      onSearchStateChange(searchKey, (prev) => ({
        ...prev,
        loading: false,
        results: [],
        error: '',
      }));
      return undefined;
    }

    let cancelled = false;
    const timerId = window.setTimeout(async () => {
      onSearchStateChange(searchKey, (prev) =>
        String(prev.keyword || '').trim() === keyword
          ? { ...prev, loading: true, error: '' }
          : prev
      );
      try {
        const items = await searchUsers(keyword);
        if (cancelled) return;
        onSearchStateChange(searchKey, (prev) =>
          String(prev.keyword || '').trim() === keyword && prev.open
            ? { ...prev, loading: false, results: items, error: '' }
            : prev
        );
      } catch (requestError) {
        if (cancelled) return;
        onSearchStateChange(searchKey, (prev) =>
          String(prev.keyword || '').trim() === keyword && prev.open
            ? {
                ...prev,
                loading: false,
                results: [],
                error: requestError?.message || '用户搜索失败',
              }
            : prev
        );
      }
    }, USER_SEARCH_DELAY_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [onSearchStateChange, searchKey, searchState?.keyword, searchState?.open, searchUsers]);

  const handleBlur = () => {
    if (blurTimerRef.current) {
      window.clearTimeout(blurTimerRef.current);
    }
    blurTimerRef.current = window.setTimeout(() => {
      onSearchStateChange(searchKey, (prev) => ({ ...prev, open: false }));
    }, 120);
  };

  const handleFocus = () => {
    if (blurTimerRef.current) {
      window.clearTimeout(blurTimerRef.current);
    }
    onSearchStateChange(searchKey, (prev) => ({ ...prev, open: true }));
  };

  const inputValue =
    String(searchState?.keyword || '') || (selectedUser ? buildUserLabel(selectedUser) : '');
  const showDropdown =
    !!searchState?.open &&
    (!!searchState?.loading ||
      !!searchState?.error ||
      (Array.isArray(searchState?.results) && searchState.results.length > 0) ||
      !!String(searchState?.keyword || '').trim());

  return (
    <div style={{ display: 'grid', gap: '6px' }}>
      <div style={{ position: 'relative' }}>
        <input
          data-testid={`${testIdPrefix}-input`}
          value={inputValue}
          onChange={(event) => onInputChange(event.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder="输入姓名、账号或用户 ID 模糊查询"
          autoComplete="off"
          style={inputStyle}
        />
        {showDropdown ? (
          <div
            data-testid={`${testIdPrefix}-results`}
            style={{
              position: 'absolute',
              zIndex: 10,
              top: 'calc(100% + 6px)',
              left: 0,
              right: 0,
              background: '#ffffff',
              border: '1px solid #d1d5db',
              borderRadius: '10px',
              boxShadow: '0 12px 30px rgba(15, 23, 42, 0.12)',
              overflow: 'hidden',
            }}
          >
            {searchState?.loading ? (
              <div style={{ padding: '10px 12px', color: '#6b7280', fontSize: '0.9rem' }}>
                正在搜索用户...
              </div>
            ) : null}
            {!searchState?.loading && searchState?.error ? (
              <div style={{ padding: '10px 12px', color: '#991b1b', fontSize: '0.9rem' }}>
                {searchState.error}
              </div>
            ) : null}
            {!searchState?.loading &&
            !searchState?.error &&
            (!searchState?.results || searchState.results.length === 0) ? (
              <div style={{ padding: '10px 12px', color: '#6b7280', fontSize: '0.9rem' }}>
                未找到匹配用户
              </div>
            ) : null}
            {!searchState?.loading && !searchState?.error
              ? (searchState.results || []).map((item) => (
                  <button
                    key={item.user_id}
                    type="button"
                    data-testid={`${testIdPrefix}-result-${item.user_id}`}
                    onMouseDown={(event) => {
                      event.preventDefault();
                      onSelectUser(item);
                    }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      border: 'none',
                      background: '#ffffff',
                      padding: '10px 12px',
                      cursor: 'pointer',
                      borderTop: '1px solid #f3f4f6',
                    }}
                  >
                    <div style={{ fontWeight: 600 }}>{buildUserLabel(item)}</div>
                    <div
                      style={{
                        color: '#6b7280',
                        fontSize: '0.8rem',
                        marginTop: '2px',
                      }}
                    >
                      {item.department_name || item.company_name || ''}
                    </div>
                  </button>
                ))
              : null}
          </div>
        ) : null}
      </div>
      <div
        data-testid={`${testIdPrefix}-selected`}
        style={{ color: '#6b7280', fontSize: '0.85rem' }}
      >
        {selectedUser
          ? `已选择用户: ${buildUserLabel(selectedUser)}`
          : '已选择用户: 未选择用户'}
      </div>
      <div style={{ color: '#9ca3af', fontSize: '0.8rem' }}>
        先输入关键词，再从下拉结果中选择用户
      </div>
    </div>
  );
}

export default function ApprovalConfig() {
  const {
    loading,
    savingKey,
    error,
    saveMessage,
    drafts,
    currentOperationType,
    currentDraft,
    searchUsers,
    updateMemberSearchState,
    loadData,
    setCurrentOperationType,
    setCurrentDraftName,
    addStep,
    removeStep,
    updateStepField,
    addMember,
    removeMember,
    updateMemberField,
    handleMemberUserKeywordChange,
    handleSelectMemberUser,
    handleSave,
    getSelectedUser,
    getMemberSearchState,
  } = useApprovalConfigPage();

  return (
    <div style={{ display: 'grid', gap: '16px' }} data-testid="approval-config-page">
      <div
        style={{
          ...cardStyle,
          display: 'flex',
          justifyContent: 'space-between',
          gap: '12px',
          flexWrap: 'wrap',
        }}
      >
        <div>
          <div style={{ fontSize: '1.2rem', fontWeight: 700, color: '#111827' }}>
            审批配置
          </div>
          <div style={{ color: '#4b5563', marginTop: '4px' }}>
            用场景下拉切换当前审批流程，支持固定用户和直属主管混合配置。
          </div>
        </div>
        <button type="button" onClick={loadData} style={buttonStyle}>
          刷新
        </button>
      </div>

      {error ? (
        <div
          data-testid="approval-config-error"
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

      {saveMessage ? (
        <div
          data-testid="approval-config-success"
          style={{
            ...cardStyle,
            borderColor: '#bbf7d0',
            background: '#f0fdf4',
            color: '#166534',
          }}
        >
          {saveMessage}
        </div>
      ) : null}

      {loading ? (
        <div style={cardStyle}>正在加载审批配置...</div>
      ) : !currentDraft ? (
        <div style={cardStyle}>暂无审批场景</div>
      ) : (
        <section
          key={currentDraft.operation_type}
          style={cardStyle}
          data-testid={`approval-config-card-${currentDraft.operation_type}`}
        >
          <div style={{ display: 'grid', gap: '14px' }}>
            <label style={{ display: 'grid', gap: '6px' }}>
              <span style={{ fontWeight: 600, color: '#111827' }}>审批场景</span>
              <select
                value={currentOperationType}
                onChange={(event) => setCurrentOperationType(event.target.value)}
                data-testid="approval-config-operation-select"
                style={{
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '10px',
                }}
              >
                {drafts.map((draft) => (
                  <option key={draft.operation_type} value={draft.operation_type}>
                    {draft.operation_label}
                  </option>
                ))}
              </select>
            </label>

            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                gap: '12px',
                flexWrap: 'wrap',
              }}
            >
              <div>
                <div style={{ fontWeight: 700, color: '#111827' }}>
                  {currentDraft.operation_label}
                </div>
                <div style={{ color: '#6b7280', marginTop: '4px' }}>
                  {currentDraft.operation_type}
                </div>
              </div>
              <button
                type="button"
                data-testid={`approval-config-save-${currentDraft.operation_type}`}
                onClick={handleSave}
                disabled={savingKey === currentDraft.operation_type}
                style={primaryButtonStyle}
              >
                {savingKey === currentDraft.operation_type ? '保存中...' : '保存'}
              </button>
            </div>

            <label style={{ display: 'grid', gap: '6px' }}>
              <span style={{ fontWeight: 600, color: '#111827' }}>工作流名称</span>
              <input
                type="text"
                value={currentDraft.name}
                data-testid={`approval-config-name-${currentDraft.operation_type}`}
                onChange={(event) => setCurrentDraftName(event.target.value)}
                style={{
                  padding: '10px 12px',
                  border: '1px solid #d1d5db',
                  borderRadius: '10px',
                }}
              />
            </label>

            {(currentDraft.steps || []).map((step, stepIndex) => (
              <div
                key={`${currentDraft.operation_type}-${step.step_no}`}
                style={{
                  border: '1px solid #e5e7eb',
                  borderRadius: '12px',
                  padding: '12px',
                }}
                data-testid={`approval-config-step-${currentDraft.operation_type}-${stepIndex}`}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    gap: '12px',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                  }}
                >
                  <strong>{`第 ${stepIndex + 1} 层`}</strong>
                  <button
                    type="button"
                    onClick={() => removeStep(stepIndex)}
                    disabled={(currentDraft.steps || []).length <= 1}
                    style={buttonStyle}
                  >
                    删除本层
                  </button>
                </div>

                <div style={{ marginTop: '12px', display: 'grid', gap: '12px' }}>
                  <label style={{ display: 'grid', gap: '6px' }}>
                    <span style={{ fontWeight: 600, color: '#111827' }}>层名称</span>
                    <input
                      type="text"
                      value={step.step_name}
                      data-testid={`approval-config-step-name-${currentDraft.operation_type}-${stepIndex}`}
                      onChange={(event) =>
                        updateStepField(stepIndex, 'step_name', event.target.value)
                      }
                      style={{
                        padding: '10px 12px',
                        border: '1px solid #d1d5db',
                        borderRadius: '10px',
                      }}
                    />
                  </label>

                  <div style={{ display: 'grid', gap: '10px' }}>
                    <div style={{ fontWeight: 600, color: '#111827' }}>审批成员</div>
                    {(step.members || []).map((member, memberIndex) => {
                      const searchKey = buildMemberSearchKey(
                        currentDraft.operation_type,
                        stepIndex,
                        memberIndex
                      );

                      return (
                        <div
                          key={`${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                          style={{
                            display: 'grid',
                            gridTemplateColumns: '180px minmax(0, 1fr) auto',
                            gap: '10px',
                            alignItems: 'center',
                          }}
                          data-testid={`approval-config-member-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                        >
                          <select
                            value={member.member_type}
                            data-testid={`approval-config-member-type-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                            onChange={(event) =>
                              updateMemberField(
                                stepIndex,
                                memberIndex,
                                'member_type',
                                event.target.value
                              )
                            }
                            style={{
                              padding: '10px 12px',
                              border: '1px solid #d1d5db',
                              borderRadius: '10px',
                            }}
                          >
                            <option value={WORKFLOW_MEMBER_TYPE_USER}>固定用户</option>
                            <option value={WORKFLOW_MEMBER_TYPE_SPECIAL_ROLE}>
                              直属主管
                            </option>
                          </select>

                          {member.member_type === WORKFLOW_MEMBER_TYPE_USER ? (
                            <UserLookupField
                              searchKey={searchKey}
                              selectedUser={getSelectedUser(member.member_ref)}
                              searchState={
                                getMemberSearchState(
                                  currentDraft.operation_type,
                                  stepIndex,
                                  memberIndex
                                ) || createUserSearchState()
                              }
                              onSearchStateChange={updateMemberSearchState}
                              onInputChange={(value) =>
                                handleMemberUserKeywordChange(
                                  currentDraft.operation_type,
                                  stepIndex,
                                  memberIndex,
                                  value
                                )
                              }
                              onSelectUser={(selectedUser) =>
                                handleSelectMemberUser(
                                  currentDraft.operation_type,
                                  stepIndex,
                                  memberIndex,
                                  selectedUser
                                )
                              }
                              searchUsers={searchUsers}
                              testIdPrefix={`approval-config-member-ref-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                            />
                          ) : (
                            <div
                              data-testid={`approval-config-member-role-${currentDraft.operation_type}-${stepIndex}-${memberIndex}`}
                              style={{
                                padding: '10px 12px',
                                border: '1px solid #d1d5db',
                                borderRadius: '10px',
                                background: '#f9fafb',
                                color: '#374151',
                              }}
                            >
                              {specialRoleLabel(member.member_ref)}
                            </div>
                          )}

                          <button
                            type="button"
                            onClick={() => removeMember(stepIndex, memberIndex)}
                            style={buttonStyle}
                          >
                            删除成员
                          </button>
                        </div>
                      );
                    })}

                    <div>
                      <button
                        type="button"
                        data-testid={`approval-config-add-member-${currentDraft.operation_type}-${stepIndex}`}
                        onClick={() => addMember(stepIndex)}
                        style={buttonStyle}
                      >
                        增加成员
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            <div>
              <button
                type="button"
                data-testid={`approval-config-add-step-${currentDraft.operation_type}`}
                onClick={addStep}
                style={buttonStyle}
              >
                增加一层
              </button>
            </div>
          </div>
        </section>
      )}
    </div>
  );
}
