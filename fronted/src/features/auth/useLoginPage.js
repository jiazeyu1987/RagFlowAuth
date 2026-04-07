import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { getDefaultLandingRoute } from './defaultLandingRoute';
import { useAuth } from '../../hooks/useAuth';

const MOBILE_BREAKPOINT = 768;

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

export default function useLoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;

    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);

    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setLoading(true);

    const result = await login(username, password);
    setLoading(false);

    if (result.success) {
      navigate(getDefaultLandingRoute(result.user));
      return;
    }

    setError(result.error || '登录失败');
  };

  return {
    username,
    password,
    error,
    loading,
    isMobile,
    setUsername,
    setPassword,
    handleSubmit,
  };
}
