export const ROOT = '';

export const HIDDEN_CHAT_NAMES = new Set(['\u5927\u6a21\u578b', '\u5c0f\u6a21\u578b', '\u95ee\u9898\u6bd4\u5bf9']);

export const emptyForm = {
  group_name: '',
  description: '',
  folder_id: null,
  accessible_kbs: [],
  accessible_kb_nodes: [],
  accessible_chats: [],
  can_upload: false,
  can_review: false,
  can_download: true,
  can_delete: false,
  can_manage_kb_directory: false,
  can_view_kb_config: true,
  can_view_tools: true,
};
