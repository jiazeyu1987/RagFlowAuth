import { pinyin } from 'pinyin-pro';

const NON_USERNAME_CHARACTERS_PATTERN = /[^a-z0-9]/g;

export const normalizeAutoUsername = (value) =>
  String(value || '')
    .trim()
    .toLowerCase()
    .replace(NON_USERNAME_CHARACTERS_PATTERN, '');

export const buildAutoUsernameFromFullName = (fullName) => {
  const normalizedFullName = String(fullName || '').trim();
  if (!normalizedFullName) {
    return '';
  }

  return normalizeAutoUsername(
    pinyin(normalizedFullName, {
      toneType: 'none',
      separator: '',
      surname: 'head',
      nonZh: 'consecutive',
      v: true,
    })
  );
};

export const shouldApplyAutoUsername = ({ currentUsername, lastAutoUsername }) => {
  const normalizedCurrentUsername = String(currentUsername || '').trim();
  const normalizedLastAutoUsername = String(lastAutoUsername || '').trim();
  return !normalizedCurrentUsername || normalizedCurrentUsername === normalizedLastAutoUsername;
};
