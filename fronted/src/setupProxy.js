const { createProxyMiddleware } = require('http-proxy-middleware');

const DEFAULT_BACKEND_TARGET = 'http://127.0.0.1:8001';

const resolveProxyTarget = () => {
  const configured = String(process.env.REACT_APP_AUTH_URL || '').trim();
  if (!configured) return DEFAULT_BACKEND_TARGET;
  return configured.endsWith('/') ? configured.slice(0, -1) : configured;
};

module.exports = function setupProxy(app) {
  const target = resolveProxyTarget();

  app.use(
    '/api',
    createProxyMiddleware({
      target,
      changeOrigin: true,
      ws: false,
      logLevel: 'warn',
    })
  );

  app.use(
    '/health',
    createProxyMiddleware({
      target,
      changeOrigin: true,
      ws: false,
      logLevel: 'warn',
    })
  );
};
