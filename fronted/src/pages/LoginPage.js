import React from 'react';

import useLoginPage from '../features/auth/useLoginPage';

const LoginPage = () => {
  const {
    username,
    password,
    error,
    loading,
    isMobile,
    setUsername,
    setPassword,
    handleSubmit,
  } = useLoginPage();

  return (
    <div style={{ minHeight: '100vh', position: 'relative', overflow: 'hidden' }}>
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          backgroundImage: "url('/login-bg.png')",
          backgroundSize: 'cover',
          backgroundPosition: 'center',
          filter: 'saturate(1.05)',
          transform: 'scale(1.02)',
        }}
      />
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'linear-gradient(90deg, rgba(2,6,23,0.72) 0%, rgba(2,6,23,0.52) 45%, rgba(2,6,23,0.35) 100%)',
        }}
      />
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          background:
            'radial-gradient(800px 500px at 25% 25%, rgba(59,130,246,0.28), transparent 60%), radial-gradient(700px 400px at 80% 55%, rgba(14,165,233,0.18), transparent 60%)',
          mixBlendMode: 'screen',
          opacity: 0.9,
        }}
      />

      <div
        style={{
          position: 'relative',
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          padding: isMobile ? '24px 12px' : '48px 20px',
        }}
      >
        <div
          style={{
            width: '100%',
            maxWidth: 1120,
            margin: '0 auto',
            display: 'grid',
            gridTemplateColumns: isMobile ? '1fr' : '1.25fr 0.85fr',
            gap: isMobile ? 18 : 28,
            alignItems: 'center',
          }}
        >
          <div style={{ color: 'white', padding: isMobile ? '0' : '10px 8px' }}>
            <div
              style={{
                fontSize: isMobile ? 24 : 28,
                fontWeight: 800,
                letterSpacing: '0.04em',
                marginBottom: 10,
                textShadow: '0 10px 30px rgba(0,0,0,0.45)',
              }}
            >
              瑞泰知识库
            </div>
            <div
              style={{
                letterSpacing: '0.14em',
                textTransform: 'uppercase',
                opacity: 0.9,
                fontSize: 12,
              }}
            >
              Knowledge Security Governance
            </div>
            <h1
              style={{
                margin: '14px 0 10px 0',
                fontSize: isMobile ? 30 : 44,
                lineHeight: 1.1,
                fontWeight: 800,
                textShadow: '0 10px 30px rgba(0,0,0,0.45)',
              }}
            >
              智能对话与知识管理
              <br />
              更安全、更可控、更易用
            </h1>
            <div
              style={{
                marginTop: 10,
                color: 'rgba(255,255,255,0.78)',
                maxWidth: 560,
                lineHeight: 1.75,
                fontSize: isMobile ? 13 : 14,
              }}
            >
              登录后可使用：AI 对话、搜索、文档浏览与审核等功能。请使用已分配的账号登录系统。
            </div>
          </div>

          <div
            style={{
              width: '100%',
              maxWidth: isMobile ? '100%' : 420,
              marginLeft: isMobile ? 0 : 'auto',
              background: 'rgba(255,255,255,0.12)',
              border: '1px solid rgba(255,255,255,0.22)',
              borderRadius: 18,
              boxShadow: '0 30px 80px rgba(0,0,0,0.45)',
              backdropFilter: 'blur(14px)',
              WebkitBackdropFilter: 'blur(14px)',
              overflow: 'hidden',
            }}
          >
            <div style={{ padding: isMobile ? 20 : 28, background: 'rgba(255,255,255,0.06)' }}>
              <div style={{ color: 'rgba(255,255,255,0.92)', fontWeight: 700, fontSize: 20 }}>
                登录
              </div>
              <div style={{ marginTop: 6, color: 'rgba(255,255,255,0.75)', fontSize: 13 }}>
                请输入用户名和密码登录系统。
              </div>
            </div>

            <div style={{ padding: isMobile ? 20 : 28, background: 'rgba(17,24,39,0.40)' }}>
              {error ? (
                <div
                  role="alert"
                  data-testid="login-error"
                  style={{
                    background: 'rgba(239,68,68,0.14)',
                    border: '1px solid rgba(239,68,68,0.35)',
                    color: 'rgba(255,255,255,0.92)',
                    padding: '10px 12px',
                    borderRadius: 10,
                    marginBottom: 16,
                    fontSize: 13,
                  }}
                >
                  {error}
                </div>
              ) : null}

              <form onSubmit={handleSubmit}>
                <div style={{ marginBottom: 18 }}>
                  <label
                    htmlFor="login-username"
                    style={{
                      display: 'block',
                      marginBottom: 8,
                      color: 'rgba(255,255,255,0.85)',
                      fontWeight: 600,
                    }}
                  >
                    用户名
                  </label>
                  <input
                    id="login-username"
                    type="text"
                    name="username"
                    data-testid="login-username"
                    autoComplete="username"
                    value={username}
                    onChange={(event) => setUsername(event.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: 12,
                      border: '1px solid rgba(255,255,255,0.22)',
                      borderRadius: 10,
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                      background: 'rgba(255,255,255,0.08)',
                      color: 'white',
                      outline: 'none',
                    }}
                    placeholder="请输入用户名"
                  />
                </div>

                <div style={{ marginBottom: 18 }}>
                  <label
                    htmlFor="login-password"
                    style={{
                      display: 'block',
                      marginBottom: 8,
                      color: 'rgba(255,255,255,0.85)',
                      fontWeight: 600,
                    }}
                  >
                    密码
                  </label>
                  <input
                    id="login-password"
                    type="password"
                    name="password"
                    data-testid="login-password"
                    autoComplete="current-password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    required
                    style={{
                      width: '100%',
                      padding: 12,
                      border: '1px solid rgba(255,255,255,0.22)',
                      borderRadius: 10,
                      fontSize: '1rem',
                      boxSizing: 'border-box',
                      background: 'rgba(255,255,255,0.08)',
                      color: 'white',
                      outline: 'none',
                    }}
                    placeholder="请输入密码"
                  />
                </div>

                <button
                  type="submit"
                  data-testid="login-submit"
                  disabled={loading}
                  style={{
                    width: '100%',
                    padding: 12,
                    background: loading
                      ? 'rgba(59,130,246,0.55)'
                      : 'linear-gradient(135deg, #60a5fa 0%, #2563eb 55%, #1d4ed8 100%)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 10,
                    fontSize: '1rem',
                    fontWeight: 700,
                    cursor: loading ? 'not-allowed' : 'pointer',
                    boxShadow: '0 16px 30px rgba(37,99,235,0.28)',
                    transition: 'transform 0.15s ease, filter 0.15s ease',
                  }}
                  onMouseEnter={(event) => {
                    if (!loading && !isMobile) {
                      event.currentTarget.style.filter = 'brightness(1.05)';
                    }
                  }}
                  onMouseLeave={(event) => {
                    if (!loading && !isMobile) {
                      event.currentTarget.style.filter = 'none';
                    }
                  }}
                  onMouseDown={(event) => {
                    if (!loading && !isMobile) {
                      event.currentTarget.style.transform = 'translateY(1px)';
                    }
                  }}
                  onMouseUp={(event) => {
                    if (!loading && !isMobile) {
                      event.currentTarget.style.transform = 'translateY(0)';
                    }
                  }}
                >
                  {loading ? '登录中...' : '登录'}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
