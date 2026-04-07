import React from 'react';

export default function ManagerAssignmentField({
  inputStyle,
  label,
  placeholder,
  value,
  required = false,
  testId,
  options,
  onChange,
  marginBottom = 16,
}) {
  return (
    <div style={{ marginBottom }}>
      <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>{label}</label>
      <select
        required={required}
        value={value || ''}
        onChange={onChange}
        data-testid={testId}
        style={{ ...inputStyle, backgroundColor: 'white' }}
      >
        <option value="" disabled>
          {placeholder}
        </option>
        {(Array.isArray(options) ? options : []).map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </div>
  );
}
