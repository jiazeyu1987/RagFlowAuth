import { authBackendUrl } from '../../config/backend';
import tokenStore from '../auth/tokenStore';

const isAbsoluteUrl = (url) => /^https?:\/\//i.test(url);

const buildUrl = (pathOrUrl) => (isAbsoluteUrl(pathOrUrl) ? pathOrUrl : authBackendUrl(pathOrUrl));

const parseMaybeJson = async (response) => {
  try {
    return await response.json();
  } catch {
    return null;
  }
};

const normalizeDisplayError = (message, fallback) => {
  const text = String(message || '').trim();
  if (!text) return fallback;
  if (/[\u4e00-\u9fff]/.test(text)) return text;
  return fallback;
};

let refreshPromise = null;
let authRedirecting = false;

const shouldAutoRedirectToLogin = (url, options = {}) => {
  if (options.skipAuth) return false;
  if (options.skipSessionRedirect) return false;
  if (url.endsWith('/api/auth/login')) return false;
  return true;
};

const redirectToLogin = () => {
  if (typeof window === 'undefined') return;
  const currentPath = String(window.location?.pathname || '');
  if (currentPath === '/login') return;
  if (authRedirecting) return;
  authRedirecting = true;
  try {
    window.location.assign('/login');
  } catch {
    window.location.href = '/login';
  }
};

const handleUnauthorizedTerminal = (url, options = {}) => {
  if (!shouldAutoRedirectToLogin(url, options)) return;
  tokenStore.clearAuth();
  redirectToLogin();
};

const refreshAccessToken = async () => {
  if (refreshPromise) return refreshPromise;

  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) {
    tokenStore.clearAuth();
    throw new Error('未找到刷新令牌');
  }

  refreshPromise = (async () => {
    const response = await fetch(buildUrl('/api/auth/refresh'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${refreshToken}`,
      },
    });

    if (!response.ok) {
      tokenStore.clearAuth();
      throw new Error('刷新令牌失败');
    }

    const data = await response.json();
    tokenStore.setAccessToken(data.access_token);
    return data.access_token;
  })();

  try {
    return await refreshPromise;
  } finally {
    refreshPromise = null;
  }
};

const withAuthHeaders = (headers, includeContentType, body, skipAuth) => {
  const merged = { ...(headers || {}) };
  const hasAuth = Object.keys(merged).some((k) => k.toLowerCase() === 'authorization');
  if (!skipAuth && !hasAuth) {
    const accessToken = tokenStore.getAccessToken();
    if (accessToken) merged['Authorization'] = `Bearer ${accessToken}`;
  }

  if (includeContentType) {
    const hasContentType = Object.keys(merged).some((k) => k.toLowerCase() === 'content-type');
    const isForm = typeof FormData !== 'undefined' && body instanceof FormData;
    if (!hasContentType && !isForm) merged['Content-Type'] = 'application/json';
  }

  return merged;
};

const request = async (pathOrUrl, options = {}) => {
  const url = buildUrl(pathOrUrl);
  const includeContentType = options.includeContentType !== false;
  const headers = withAuthHeaders(options.headers, includeContentType, options.body, options.skipAuth);
  let response = null;
  try {
    response = await fetch(url, { ...options, headers });
  } catch {
    throw new Error('网络请求失败，请检查连接后重试');
  }

  if (response.status !== 401) return response;

  if (options.skipRefresh) {
    handleUnauthorizedTerminal(url, options);
    return response;
  }
  if (url.endsWith('/api/auth/refresh')) {
    handleUnauthorizedTerminal(url, options);
    return response;
  }

  const refreshToken = tokenStore.getRefreshToken();
  if (!refreshToken) {
    handleUnauthorizedTerminal(url, options);
    return response;
  }

  try {
    await refreshAccessToken();
  } catch {
    handleUnauthorizedTerminal(url, options);
    return response;
  }

  const retryHeaders = withAuthHeaders(options.headers, includeContentType, options.body, options.skipAuth);
  let retryResponse = null;
  try {
    retryResponse = await fetch(url, { ...options, headers: retryHeaders });
  } catch {
    throw new Error('网络请求失败，请检查连接后重试');
  }
  if (retryResponse.status === 401) {
    handleUnauthorizedTerminal(url, options);
  }
  return retryResponse;
};

const requestJson = async (pathOrUrl, options = {}) => {
  const response = await request(pathOrUrl, options);
  if (response.ok) return response.json();

  const data = await parseMaybeJson(response);
  const message = normalizeDisplayError(
    data?.detail || data?.message || data?.error,
    `请求失败（状态码：${response.status}）`
  );
  const error = new Error(message);
  error.status = response.status;
  error.data = data;
  throw error;
};

export const httpClient = {
  request,
  requestJson,
  refreshAccessToken,
};
