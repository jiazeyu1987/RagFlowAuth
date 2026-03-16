import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import './LoginPage.css';

const LoginPage = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(username, password);
    setLoading(false);

    if (result.success) {
      navigate('/chat');
      return;
    }

    setError(result.error || '登录失败');
  };

  return (
    <div className="medical-login">
      <div className="medical-login__bg" aria-hidden="true" />
      <div className="medical-login__shell">
        <section className="medical-login__intro">
          <p className="medical-login__kicker">精神心理领域数据库智能分析系统</p>
          <h1 className="medical-login__title">医生工作台登录入口</h1>
          <p className="medical-login__desc">
            面向医疗场景的智能知识系统，支持规范化检索、对话分析、文档管理与安全审计，帮助医生快速获取可信依据。
          </p>
          <div className="medical-login__tips">
            <div className="medical-login__tip">高可读信息布局，减少操作跳转</div>
            <div className="medical-login__tip">重点流程保留权限与审计能力</div>
            <div className="medical-login__tip">临床使用场景优先的界面设计</div>
          </div>
        </section>

        <section className="medical-login__panel">
          <div className="medical-login__panel-head">
            <h2>账号登录</h2>
            <p>请输入用户名和密码进入系统。</p>
            <div data-testid="login-super-admin-banner" className="medical-login__super-admin">
              测试超级管理员账号：SuperAdmin / SuperAdmin
            </div>
          </div>

          <div className="medical-login__panel-body">
            {error ? (
              <div role="alert" data-testid="login-error" className="medical-login__error">
                {error}
              </div>
            ) : null}

            <form onSubmit={handleSubmit}>
              <div className="medical-login__field">
                <label htmlFor="login-username">用户名</label>
                <input
                  id="login-username"
                  type="text"
                  name="username"
                  data-testid="login-username"
                  autoComplete="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  placeholder="请输入用户名"
                />
              </div>

              <div className="medical-login__field">
                <label htmlFor="login-password">密码</label>
                <input
                  id="login-password"
                  type="password"
                  name="password"
                  data-testid="login-password"
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  placeholder="请输入密码"
                />
              </div>

              <button type="submit" data-testid="login-submit" disabled={loading} className="medical-login__submit">
                {loading ? '登录中...' : '登录'}
              </button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
};

export default LoginPage;
