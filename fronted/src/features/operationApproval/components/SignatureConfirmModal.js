import React, { useEffect, useState } from 'react';

export function SignatureConfirmModal({
  prompt,
  submitting,
  error,
  onClose,
  onSubmit,
}) {
  const [password, setPassword] = useState('');
  const [meaning, setMeaning] = useState('');
  const [reason, setReason] = useState('');

  useEffect(() => {
    if (!prompt) {
      setPassword('');
      setMeaning('');
      setReason('');
      return;
    }
    setPassword('');
    setMeaning(prompt.defaultMeaning || '');
    setReason(prompt.defaultReason || '');
  }, [prompt]);

  if (!prompt) {
    return null;
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSubmit({
      password,
      signatureMeaning: meaning.trim(),
      signatureReason: reason.trim(),
    });
  };

  return (
    <div
      data-testid="review-signature-modal"
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(17, 24, 39, 0.45)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px',
        zIndex: 70,
      }}
      onClick={submitting ? undefined : onClose}
    >
      <form
        onSubmit={handleSubmit}
        style={{
          width: 'min(520px, 100%)',
          background: '#ffffff',
          borderRadius: '12px',
          border: '1px solid #d1d5db',
          boxShadow: '0 20px 45px rgba(15, 23, 42, 0.18)',
          padding: '20px',
          display: 'grid',
          gap: '12px',
        }}
        onClick={(event) => event.stopPropagation()}
      >
        <div>
          <div style={{ fontSize: '1.05rem', fontWeight: 700, color: '#111827' }}>
            {prompt.title || '电子签名'}
          </div>
          {prompt.description ? (
            <div style={{ marginTop: '6px', color: '#4b5563', lineHeight: 1.5 }}>
              {prompt.description}
            </div>
          ) : null}
        </div>

        <label style={{ display: 'grid', gap: '6px' }}>
          <span style={{ color: '#111827', fontWeight: 600 }}>当前密码</span>
          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            data-testid="review-signature-password"
            autoComplete="current-password"
            disabled={submitting}
            style={{
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              fontSize: '0.95rem',
            }}
          />
        </label>

        <label style={{ display: 'grid', gap: '6px' }}>
          <span style={{ color: '#111827', fontWeight: 600 }}>签名含义</span>
          <input
            type="text"
            value={meaning}
            onChange={(event) => setMeaning(event.target.value)}
            data-testid="review-signature-meaning"
            disabled={submitting}
            style={{
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              fontSize: '0.95rem',
            }}
          />
        </label>

        <label style={{ display: 'grid', gap: '6px' }}>
          <span style={{ color: '#111827', fontWeight: 600 }}>原因</span>
          <textarea
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            data-testid="review-signature-reason"
            disabled={submitting}
            rows={4}
            style={{
              padding: '10px 12px',
              border: '1px solid #d1d5db',
              borderRadius: '8px',
              fontSize: '0.95rem',
              resize: 'vertical',
            }}
          />
        </label>

        {error ? (
          <div
            data-testid="review-signature-error"
            style={{
              background: '#fee2e2',
              border: '1px solid #fecaca',
              color: '#991b1b',
              borderRadius: '8px',
              padding: '10px 12px',
            }}
          >
            {error}
          </div>
        ) : null}

        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px' }}>
          <button
            type="button"
            onClick={onClose}
            data-testid="review-signature-cancel"
            disabled={submitting}
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: '1px solid #d1d5db',
              background: '#ffffff',
              color: '#111827',
              cursor: submitting ? 'not-allowed' : 'pointer',
            }}
          >
            取消
          </button>
          <button
            type="submit"
            data-testid="review-signature-submit"
            disabled={submitting}
            style={{
              padding: '10px 14px',
              borderRadius: '8px',
              border: 'none',
              background: submitting ? '#9ca3af' : '#2563eb',
              color: '#ffffff',
              cursor: submitting ? 'not-allowed' : 'pointer',
            }}
          >
            {submitting ? '签名中...' : (prompt.confirmLabel || '确认签名')}
          </button>
        </div>
      </form>
    </div>
  );
}

export default SignatureConfirmModal;
