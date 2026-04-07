export const authBackendUrl = (path) => {
  const configured = process.env.REACT_APP_AUTH_URL;
  const normalizedConfigured =
    configured && configured.endsWith('/') ? configured.slice(0, -1) : configured;

  // Dev default: use the CRA proxy so browser requests stay same-origin.
  if (process.env.NODE_ENV !== 'production') {
    if (!normalizedConfigured) return path;
    return `${normalizedConfigured}${path}`;
  }

  // Production default: same-origin (recommended when served behind Nginx reverse proxy).
  if (!normalizedConfigured) return path;
  return `${normalizedConfigured}${path}`;
};

export default authBackendUrl;
