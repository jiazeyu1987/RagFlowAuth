import React, { useEffect, useRef, useState } from 'react';
import { buildUserLabel } from '../../operationApproval/approvalConfigHelpers';
import { mapUserFacingErrorMessage } from '../../../shared/errors/userFacingErrorMessages';

const SEARCH_DELAY_MS = 250;

const chipStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: '8px',
  padding: '6px 10px',
  borderRadius: '999px',
  background: '#eff6ff',
  color: '#1d4ed8',
  border: '1px solid #bfdbfe',
  fontSize: '0.85rem',
};

export default function QualitySystemUserMultiSelect({
  selectedUsers,
  onChange,
  onSearch,
  testIdPrefix,
}) {
  const blurTimerRef = useRef(null);
  const [keyword, setKeyword] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState('');

  useEffect(
    () => () => {
      if (blurTimerRef.current) {
        window.clearTimeout(blurTimerRef.current);
      }
    },
    []
  );

  useEffect(() => {
    const cleanKeyword = String(keyword || '').trim();
    if (!open) return undefined;
    if (!cleanKeyword) {
      setResults([]);
      setLoading(false);
      setError('');
      return undefined;
    }

    let cancelled = false;
    const timerId = window.setTimeout(async () => {
      setLoading(true);
      setError('');
      try {
        const items = await onSearch(cleanKeyword);
        if (cancelled) return;
        const selectedIds = new Set((selectedUsers || []).map((item) => item.user_id));
        setResults((items || []).filter((item) => !selectedIds.has(item.user_id)));
      } catch (requestError) {
        if (cancelled) return;
        setResults([]);
        setError(
          mapUserFacingErrorMessage(requestError?.message, 'Failed to search assignable users.')
        );
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }, SEARCH_DELAY_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timerId);
    };
  }, [keyword, onSearch, open, selectedUsers]);

  const handleBlur = () => {
    if (blurTimerRef.current) {
      window.clearTimeout(blurTimerRef.current);
    }
    blurTimerRef.current = window.setTimeout(() => setOpen(false), 120);
  };

  const handleFocus = () => {
    if (blurTimerRef.current) {
      window.clearTimeout(blurTimerRef.current);
    }
    setOpen(true);
  };

  const handleAddUser = (user) => {
    const nextUsers = [...(selectedUsers || []), user];
    onChange(nextUsers);
    setKeyword('');
    setResults([]);
    setOpen(false);
  };

  const handleRemoveUser = (userId) => {
    onChange((selectedUsers || []).filter((item) => item.user_id !== userId));
  };

  const showDropdown =
    open &&
    (loading || error || results.length > 0 || String(keyword || '').trim());

  return (
    <div style={{ display: 'grid', gap: '8px' }}>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
        {(selectedUsers || []).map((user) => (
          <span key={user.user_id} style={chipStyle} data-testid={`${testIdPrefix}-chip-${user.user_id}`}>
            <span>{buildUserLabel(user)}</span>
            <button
              type="button"
              onClick={() => handleRemoveUser(user.user_id)}
              style={{
                border: 'none',
                background: 'transparent',
                color: '#1d4ed8',
                cursor: 'pointer',
                padding: 0,
                fontSize: '0.9rem',
              }}
              data-testid={`${testIdPrefix}-remove-${user.user_id}`}
            >
              x
            </button>
          </span>
        ))}
      </div>

      <div style={{ position: 'relative' }}>
        <input
          value={keyword}
          onChange={(event) => setKeyword(event.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder="Search active users by name, username, or employee id"
          autoComplete="off"
          data-testid={`${testIdPrefix}-input`}
          style={{
            width: '100%',
            padding: '10px 12px',
            borderRadius: '10px',
            border: '1px solid #cbd5e1',
            boxSizing: 'border-box',
          }}
        />

        {showDropdown ? (
          <div
            style={{
              position: 'absolute',
              zIndex: 20,
              top: 'calc(100% + 6px)',
              left: 0,
              right: 0,
              background: '#ffffff',
              border: '1px solid #d1d5db',
              borderRadius: '10px',
              boxShadow: '0 12px 30px rgba(15, 23, 42, 0.12)',
              overflow: 'hidden',
            }}
            data-testid={`${testIdPrefix}-results`}
          >
            {loading ? (
              <div style={{ padding: '10px 12px', color: '#64748b' }}>Searching users...</div>
            ) : null}
            {!loading && error ? (
              <div style={{ padding: '10px 12px', color: '#b91c1c' }}>{error}</div>
            ) : null}
            {!loading && !error && results.length === 0 ? (
              <div style={{ padding: '10px 12px', color: '#64748b' }}>No matching users found.</div>
            ) : null}
            {!loading && !error
              ? results.map((user) => (
                  <button
                    key={user.user_id}
                    type="button"
                    onMouseDown={(event) => {
                      event.preventDefault();
                      handleAddUser(user);
                    }}
                    style={{
                      width: '100%',
                      textAlign: 'left',
                      border: 'none',
                      background: '#ffffff',
                      cursor: 'pointer',
                      padding: '10px 12px',
                      borderTop: '1px solid #f1f5f9',
                    }}
                    data-testid={`${testIdPrefix}-result-${user.user_id}`}
                  >
                    <div style={{ fontWeight: 600 }}>{buildUserLabel(user)}</div>
                    <div style={{ color: '#64748b', fontSize: '0.8rem', marginTop: '2px' }}>
                      {String(user.employee_user_id || '') || String(user.username || '')}
                    </div>
                  </button>
                ))
              : null}
          </div>
        ) : null}
      </div>
    </div>
  );
}
