import { authBackendUrl } from '../../config/backend';
import { httpClient as sharedHttpClient } from '../../shared/http/httpClient';

export const httpClient = sharedHttpClient;

export const buildAuthUrl = (path) => authBackendUrl(path);

export async function readErrorDetail(response, fallbackMessage) {
  try {
    const data = await response.json();
    return data?.detail || fallbackMessage;
  } catch {
    return fallbackMessage;
  }
}
