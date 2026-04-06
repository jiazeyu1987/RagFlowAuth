import { useCallback, useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import meApi from './api';

const MOBILE_BREAKPOINT = 768;
const COMMON_PASSWORDS = new Set(['password', '123456', 'abc123', 'qwerty', 'admin']);
const DEFAULT_SUBMIT_ERROR = '修改密码失败';

const CHANGE_PASSWORD_ERROR_MESSAGES = {
  user_not_found: '用户不存在或登录状态已失效',
  password_change_disabled: '当前账户不允许修改密码',
  old_password_incorrect: '旧密码错误',
  new_password_too_short: '密码不符合要求：密码长度至少 6 个字符',
  new_password_same_as_old: '新密码不能与旧密码相同',
  new_password_requirements_not_met: '密码不符合要求：必须包含字母和数字，且不能使用常见密码',
  new_password_reused_from_recent_history: '新密码不能与最近使用过的密码相同',
};

const CHANGE_PASSWORD_SUCCESS_MESSAGES = {
  password_changed: '密码修改成功',
};

const hasLetter = (value) =>
  Array.from(String(value || '')).some((character) => character.toLowerCase() !== character.toUpperCase());

const getInitialIsMobile = () => {
  if (typeof window === 'undefined') return false;
  return window.innerWidth <= MOBILE_BREAKPOINT;
};

const mapChangePasswordErrorMessage = (code) => {
  if (typeof code !== 'string' || !code.trim()) {
    return DEFAULT_SUBMIT_ERROR;
  }
  return CHANGE_PASSWORD_ERROR_MESSAGES[code] || code;
};

const mapChangePasswordSuccessMessage = (code) => {
  if (typeof code !== 'string' || !code.trim()) {
    return CHANGE_PASSWORD_SUCCESS_MESSAGES.password_changed;
  }
  return CHANGE_PASSWORD_SUCCESS_MESSAGES[code] || code;
};

export default function useChangePasswordPage() {
  const { user } = useAuth();
  const [isMobile, setIsMobile] = useState(getInitialIsMobile);
  const [oldPassword, setOldPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  const passwordPolicyChecks = useMemo(() => {
    const value = String(newPassword || '');
    const lowerValue = value.toLowerCase();
    const hasMinLength = value.length >= 6;
    const containsLetter = hasLetter(value);
    const containsNumber = /\d/.test(value);
    const notCommonPassword = !COMMON_PASSWORDS.has(lowerValue);
    const differsFromOldPassword = Boolean(oldPassword) && value !== oldPassword;

    return [
      { key: 'min-length', label: '至少 6 个字符', passed: hasMinLength },
      { key: 'has-letter', label: '包含至少 1 个字母', passed: containsLetter },
      { key: 'has-number', label: '包含至少 1 个数字', passed: containsNumber },
      { key: 'not-common', label: '不能是常见弱密码', passed: notCommonPassword },
      { key: 'diff-old', label: '新密码不能与旧密码相同', passed: differsFromOldPassword },
    ];
  }, [newPassword, oldPassword]);

  const passwordPolicyPassed = useMemo(
    () => passwordPolicyChecks.every((item) => item.passed),
    [passwordPolicyChecks]
  );

  useEffect(() => {
    if (typeof window === 'undefined') return undefined;
    const handleResize = () => setIsMobile(window.innerWidth <= MOBILE_BREAKPOINT);
    handleResize();
    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const handleSubmit = useCallback(
    async (event) => {
      event.preventDefault();
      setError(null);
      setMessage(null);

      if (!oldPassword || !newPassword) {
        setError('请输入旧密码和新密码');
        return;
      }
      if (!passwordPolicyPassed) {
        setError('新密码不符合安全策略，请根据红色提示调整');
        return;
      }
      if (newPassword !== confirmPassword) {
        setError('两次输入的新密码不一致');
        return;
      }

      try {
        setSubmitting(true);
        const result = await meApi.changePassword(oldPassword, newPassword);
        setMessage(mapChangePasswordSuccessMessage(result.message));
        setOldPassword('');
        setNewPassword('');
        setConfirmPassword('');
      } catch (requestError) {
        setError(mapChangePasswordErrorMessage(requestError?.message));
      } finally {
        setSubmitting(false);
      }
    },
    [confirmPassword, newPassword, oldPassword, passwordPolicyPassed]
  );

  return {
    user,
    isMobile,
    oldPassword,
    newPassword,
    confirmPassword,
    submitting,
    error,
    message,
    passwordPolicyChecks,
    passwordPolicyPassed,
    setOldPassword,
    setNewPassword,
    setConfirmPassword,
    handleSubmit,
  };
}
