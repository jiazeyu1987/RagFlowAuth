import React from 'react';
import { useLocation, Link } from 'react-router-dom';

const Unauthorized = () => {
  const location = useLocation();

  return (
    <div className="admin-med-page" style={{ maxWidth: 760 }}>
      <section className="medui-surface medui-card-pad">
        <h2 style={{ marginTop: 0, marginBottom: 8, color: '#a53a3a' }} data-testid="unauthorized-title">无权限访问</h2>
        <div className="admin-med-inline-note" style={{ marginBottom: 14 }}>
          当前账号没有权限访问该页面：<span className="admin-med-code">{location.pathname}</span>
        </div>
        <Link to="/" className="medui-btn medui-btn--secondary" style={{ display: 'inline-flex', alignItems: 'center', textDecoration: 'none' }}>
          返回首页
        </Link>
      </section>
    </div>
  );
};

export default Unauthorized;
