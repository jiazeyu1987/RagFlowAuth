export const authBackendUrl = (path) => {
  const configured = process.env.REACT_APP_AUTH_URL;

  // Dev default: talk to localhost backend.
  if (process.env.NODE_ENV !== 'production') {
    const baseUrl = configured || 'http://localhost:8001';
    return `${baseUrl}${path}`;
  }

  // Production default: same-origin (recommended when served behind Nginx reverse proxy).
  if (!configured) return path;

  // Normalize trailing slash
  const baseUrl = configured.endsWith('/') ? configured.slice(0, -1) : configured;
  return `${baseUrl}${path}`;
};

export default authBackendUrl;
