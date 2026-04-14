import React from 'react';
import { useLocation, Link } from 'react-router-dom';

const Unauthorized = () => {
  const location = useLocation();

  return (
    <div style={{ maxWidth: 720, width: '100%' }}>
      <h2 style={{ marginTop: 0 }} data-testid="unauthorized-title">Access Denied</h2>
      <div style={{ color: '#6b7280', marginBottom: 16, wordBreak: 'break-all' }}>
        Your account does not have permission to access this page: {location.pathname}
      </div>
      <Link to="/" style={{ color: '#2563eb', textDecoration: 'none' }}>
        Return to Home
      </Link>
    </div>
  );
};

export default Unauthorized;
