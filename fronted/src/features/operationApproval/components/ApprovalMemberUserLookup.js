import React, { useEffect, useRef } from 'react';
import { buildUserLabel } from '../approvalConfigHelpers';
import { inputStyle } from '../pageStyles';

const USER_SEARCH_DELAY_MS = 250;

export default function ApprovalMemberUserLookup({
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
