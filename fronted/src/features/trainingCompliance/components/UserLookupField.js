import React, { useEffect, useRef } from 'react';
import {
  helperTextStyle,
  inputStyle,
  labelStyle,
  selectedUserTextStyle,
  userLookupContainerStyle,
  userSearchDropdownStyle,
  userSearchErrorStyle,
  userSearchMessageStyle,
  userSearchMetaStyle,
  userSearchOptionStyle,
} from '../pageStyles';

export default function UserLookupField({
  label,
  placeholder,
  selectedUser,
  searchState,
  onInputChange,
  onFocus,
  onBlur,
  onSelectUser,
  testIdPrefix,
  text,
  buildUserLabel,
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

  const handleBlur = () => {
    if (blurTimerRef.current) {
      window.clearTimeout(blurTimerRef.current);
    }
    blurTimerRef.current = window.setTimeout(() => {
      onBlur();
    }, 120);
  };

  const handleFocus = () => {
    if (blurTimerRef.current) {
      window.clearTimeout(blurTimerRef.current);
    }
    onFocus();
  };

  const showDropdown = searchState.open && (
    searchState.loading
    || !!searchState.error
    || searchState.results.length > 0
    || String(searchState.keyword || '').trim()
  );

  return (
    <label style={labelStyle}>
      <span>{label}</span>
      <div style={userLookupContainerStyle}>
        <input
          data-testid={`${testIdPrefix}-input`}
          value={searchState.keyword}
          onChange={(event) => onInputChange(event.target.value)}
          onFocus={handleFocus}
          onBlur={handleBlur}
          placeholder={placeholder}
          autoComplete="off"
          style={inputStyle}
        />
        {showDropdown ? (
          <div data-testid={`${testIdPrefix}-results`} style={userSearchDropdownStyle}>
            {searchState.loading ? (
              <div style={userSearchMessageStyle}>{text.userSearchLoading}</div>
            ) : null}
            {!searchState.loading && searchState.error ? (
              <div style={userSearchErrorStyle}>{searchState.error}</div>
            ) : null}
            {!searchState.loading && !searchState.error && searchState.results.length === 0 ? (
              <div style={userSearchMessageStyle}>{text.userSearchEmpty}</div>
            ) : null}
            {!searchState.loading && !searchState.error
              ? searchState.results.map((item) => (
                <button
                  key={item.user_id}
                  type="button"
                  data-testid={`${testIdPrefix}-result-${item.user_id}`}
                  onMouseDown={(event) => {
                    event.preventDefault();
                    onSelectUser(item);
                  }}
                  style={userSearchOptionStyle}
                >
                  <div style={{ fontWeight: 600 }}>{buildUserLabel(item)}</div>
                  <div style={userSearchMetaStyle}>
                    {item.department_name || item.company_name || ''}
                  </div>
                </button>
              ))
              : null}
          </div>
        ) : null}
      </div>
      <div data-testid={`${testIdPrefix}-selected`} style={selectedUserTextStyle}>
        {selectedUser
          ? `${text.selectedUser}: ${buildUserLabel(selectedUser)}`
          : `${text.selectedUser}: ${text.noSelectedUser}`}
      </div>
      <div style={helperTextStyle}>{text.userSearchHint}</div>
    </label>
  );
}
