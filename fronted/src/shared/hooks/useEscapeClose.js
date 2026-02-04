import { useEffect } from 'react';

export function useEscapeClose(isOpen, onClose) {
  useEffect(() => {
    if (!isOpen) return;

    const handler = (e) => {
      if (e.key !== 'Escape') return;
      e.preventDefault();
      onClose?.();
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, onClose]);
}

