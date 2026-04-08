export const MOBILE_BREAKPOINT = 768;

export const LAYOUT_TEXT = {
  appName: '\u77e5\u8bc6\u5e93\u7cfb\u7edf',
  logout: '\u9000\u51fa',
  roles: {
    admin: '\u7ba1\u7406\u5458',
    subAdmin: '\u5b50\u7ba1\u7406\u5458',
    viewer: '\u666e\u901a\u7528\u6237',
  },
};

export const formatRoleLabel = (role) => {
  const value = String(role || '').trim();
  if (value === 'admin') return LAYOUT_TEXT.roles.admin;
  if (value === 'sub_admin') return LAYOUT_TEXT.roles.subAdmin;
  if (value === 'viewer') return LAYOUT_TEXT.roles.viewer;
  return '';
};
