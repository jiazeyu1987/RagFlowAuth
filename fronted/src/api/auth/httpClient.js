import { authBackendUrl } from '../../config/backend';
import { httpClient as sharedHttpClient } from '../../shared/http/httpClient';

export const httpClient = sharedHttpClient;

export const buildAuthUrl = (path) => authBackendUrl(path);

const normalizeDisplayError = (message, fallbackMessage) => {
  const text = String(message || '').trim();
  if (!text) return fallbackMessage;
  if (/[\u4e00-\u9fff]/.test(text)) return text;
  return fallbackMessage;
};

export async function readErrorDetail(response, fallbackMessage) {
  try {
    const data = await response.json();
    return normalizeDisplayError(data?.detail || data?.message || data?.error, fallbackMessage);
  } catch {
    return fallbackMessage;
  }
}
