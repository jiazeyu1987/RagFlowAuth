import { useCallback, useRef, useState } from 'react';
import authClient from '../../api/authClient';

const SIGNATURE_CANCELLED = '__signature_cancelled__';

export function useSignaturePrompt() {
  const [signaturePrompt, setSignaturePrompt] = useState(null);
  const [signatureSubmitting, setSignatureSubmitting] = useState(false);
  const [signatureError, setSignatureError] = useState(null);
  const resolverRef = useRef(null);

  const resetPrompt = useCallback(() => {
    setSignaturePrompt(null);
    setSignatureSubmitting(false);
    setSignatureError(null);
  }, []);

  const requestSignature = useCallback((prompt) => new Promise((resolve, reject) => {
    resolverRef.current = { resolve, reject };
    setSignatureError(null);
    setSignatureSubmitting(false);
    setSignaturePrompt(prompt);
  }), []);

  const closeSignaturePrompt = useCallback(() => {
    const resolver = resolverRef.current;
    resolverRef.current = null;
    resetPrompt();
    if (resolver) {
      resolver.reject(new Error(SIGNATURE_CANCELLED));
    }
  }, [resetPrompt]);

  const submitSignaturePrompt = useCallback(async ({ password, signatureMeaning, signatureReason }) => {
    const resolver = resolverRef.current;
    if (!resolver) return;

    setSignatureSubmitting(true);
    setSignatureError(null);
    try {
      const challenge = await authClient.requestSignatureChallenge(password);
      resolverRef.current = null;
      resetPrompt();
      resolver.resolve({
        sign_token: challenge.sign_token,
        signature_meaning: String(signatureMeaning || '').trim(),
        signature_reason: String(signatureReason || '').trim(),
      });
    } catch (error) {
      setSignatureSubmitting(false);
      setSignatureError(error?.message || '电子签名失败');
    }
  }, [resetPrompt]);

  const promptSignature = useCallback(async (prompt) => {
    try {
      return await requestSignature(prompt);
    } catch (error) {
      if (error?.message === SIGNATURE_CANCELLED) {
        return null;
      }
      throw error;
    }
  }, [requestSignature]);

  return {
    closeSignaturePrompt,
    promptSignature,
    signatureError,
    signaturePrompt,
    signatureSubmitting,
    submitSignaturePrompt,
  };
}

export default useSignaturePrompt;
