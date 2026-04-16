export const authBackendUrl = (path) => {
  const configured = process.env.REACT_APP_AUTH_URL;
  const normalizedConfigured =
    configured && configured.endsWith('/') ? configured.slice(0, -1) : configured;

  // 开发环境默认使用 CRA 代理，保持浏览器请求同源。
  if (process.env.NODE_ENV !== 'production') {
    if (!normalizedConfigured) return path;
    return `${normalizedConfigured}${path}`;
  }

  // 生产环境默认保持同源，适用于经 Nginx 反向代理提供服务的场景。
  if (!normalizedConfigured) return path;
  return `${normalizedConfigured}${path}`;
};

export default authBackendUrl;
