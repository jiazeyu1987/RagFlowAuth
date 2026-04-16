export const STORAGE_KEYS = Object.freeze({
  // 新后端（FastAPI + AuthX）使用的键名
  ACCESS_TOKEN: 'accessToken',
  REFRESH_TOKEN: 'refreshToken',

  // 旧后端（Flask + Casbin）使用的键名（保留向后兼容）
  AUTH_TOKEN: 'authToken',

  // 通用键名
  USER: 'user',
  APP_VERSION: 'appVersion',
  LAST_ROLE_MAP: 'lastUserRoleMap',
});
