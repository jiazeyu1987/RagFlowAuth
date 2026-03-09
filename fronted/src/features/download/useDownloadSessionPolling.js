import { useEffect } from 'react';
import { isSessionActive } from './downloadPageUtils';

export default function useDownloadSessionPolling({
  sessionId,
  sessionStatus,
  loadSession,
  onSessionData,
  onSessionError,
  intervalMs = 1200,
  enabled = true,
}) {
  useEffect(() => {
    if (!enabled) return undefined;
    if (!sessionId || !isSessionActive(sessionStatus)) return undefined;
    if (typeof loadSession !== 'function') return undefined;

    let alive = true;
    const tick = async () => {
      try {
        const data = await loadSession(sessionId);
        if (!alive) return;
        if (typeof onSessionData === 'function') onSessionData(data);
      } catch (err) {
        if (!alive) return;
        if (typeof onSessionError === 'function') onSessionError(err);
      }
    };

    tick();
    const timer = window.setInterval(tick, intervalMs);
    return () => {
      alive = false;
      window.clearInterval(timer);
    };
  }, [enabled, intervalMs, loadSession, onSessionData, onSessionError, sessionId, sessionStatus]);
}
