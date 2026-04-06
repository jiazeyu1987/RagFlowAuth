export const CHANNEL_TYPES = ['email', 'dingtalk', 'in_app'];

export const DEFAULTS = {
  email: { channelId: 'email-main', name: '邮件通知', enabled: false },
  dingtalk: { channelId: 'dingtalk-main', name: '钉钉工作通知', enabled: false },
  in_app: { channelId: 'inapp-main', name: '站内信', enabled: true },
};

export const DINGTALK_DEFAULT_RECIPIENT_MAP = {
  '025247281136343306': '025247281136343306',
  '3245020131886184': '3245020131886184',
  '204548010024278804': '204548010024278804',
};

export const DINGTALK_FORM_DEFAULTS = {
  app_key: 'dingidnt7v7zbm5tqzyn',
  app_secret: 'gi-v0YEkV_SCwXo9vGvYgBJzEbQ4wS4WUXDwA7ZkqMuNflFu0JfdFW1TeJIxcOjC',
  agent_id: '4432005762',
  recipient_map_text: JSON.stringify(DINGTALK_DEFAULT_RECIPIENT_MAP, null, 2),
  api_base: 'https://api.dingtalk.com',
  oapi_base: 'https://oapi.dingtalk.com',
  timeout_seconds: '30',
};

export const INITIAL_HISTORY_FILTERS = {
  eventType: '',
  channelType: '',
  status: '',
};
