import { authBackendUrl } from './backend';

describe('authBackendUrl', () => {
  const originalNodeEnv = process.env.NODE_ENV;
  const originalAuthUrl = process.env.REACT_APP_AUTH_URL;

  afterEach(() => {
    process.env.NODE_ENV = originalNodeEnv;
    if (originalAuthUrl === undefined) {
      delete process.env.REACT_APP_AUTH_URL;
    } else {
      process.env.REACT_APP_AUTH_URL = originalAuthUrl;
    }
  });

  it('uses same-origin paths in development when no backend override is configured', () => {
    process.env.NODE_ENV = 'development';
    delete process.env.REACT_APP_AUTH_URL;

    expect(authBackendUrl('/api/knowledge/documents')).toBe('/api/knowledge/documents');
  });

  it('uses the configured backend override in development', () => {
    process.env.NODE_ENV = 'development';
    process.env.REACT_APP_AUTH_URL = 'http://localhost:8001/';

    expect(authBackendUrl('/api/knowledge/documents')).toBe('http://localhost:8001/api/knowledge/documents');
  });

  it('uses same-origin paths in production when no backend override is configured', () => {
    process.env.NODE_ENV = 'production';
    delete process.env.REACT_APP_AUTH_URL;

    expect(authBackendUrl('/api/knowledge/documents')).toBe('/api/knowledge/documents');
  });

  it('uses the configured backend override in production', () => {
    process.env.NODE_ENV = 'production';
    process.env.REACT_APP_AUTH_URL = 'http://auth.local/';

    expect(authBackendUrl('/api/knowledge/documents')).toBe('http://auth.local/api/knowledge/documents');
  });
});
