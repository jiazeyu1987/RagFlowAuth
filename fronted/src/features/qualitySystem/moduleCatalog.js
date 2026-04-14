import { QUALITY_CAPABILITY_ACTIONS } from '../../shared/auth/capabilities';

export const QUALITY_SYSTEM_ROOT_PATH = '/quality-system';

const freezePermission = (resource, action) => Object.freeze({ resource, action });

const buildAnyPermissions = (resource, actions) => Object.freeze(
  (Array.isArray(actions) ? actions : []).map((action) => freezePermission(resource, action))
);

export const QUALITY_SYSTEM_MODULES = Object.freeze([
  Object.freeze({
    key: 'doc-control',
    path: `${QUALITY_SYSTEM_ROOT_PATH}/doc-control`,
    title: '\u6587\u63a7\u57fa\u7ebf',
    owner: 'WS01',
    resource: 'document_control',
    summary: '\u53d7\u63a7\u6587\u4ef6\u3001\u7248\u672c\u751f\u6548\u4e0e\u4f5c\u5e9f\u7ba1\u7406\u5de5\u4f5c\u533a\u3002',
    actions: QUALITY_CAPABILITY_ACTIONS.document_control,
    accessAnyPermissions: buildAnyPermissions('document_control', QUALITY_CAPABILITY_ACTIONS.document_control),
  }),
  Object.freeze({
    key: 'training',
    path: `${QUALITY_SYSTEM_ROOT_PATH}/training`,
    title: '\u57f9\u8bad\u4e0e\u77e5\u6653',
    owner: 'WS03',
    resource: 'training_ack',
    summary: '\u57f9\u8bad\u5206\u6d3e\u3001\u77e5\u6653\u786e\u8ba4\u4e0e\u7591\u95ee\u95ed\u73af\u5de5\u4f5c\u533a\u3002',
    actions: QUALITY_CAPABILITY_ACTIONS.training_ack,
    accessAnyPermissions: buildAnyPermissions('training_ack', QUALITY_CAPABILITY_ACTIONS.training_ack),
  }),
  Object.freeze({
    key: 'change-control',
    path: `${QUALITY_SYSTEM_ROOT_PATH}/change-control`,
    title: '\u53d8\u66f4\u63a7\u5236',
    owner: 'WS04',
    resource: 'change_control',
    summary: '\u53d8\u66f4\u53f0\u8d26\u3001\u8bc4\u4f30\u3001\u8ba1\u5212\u4e0e\u5173\u95ed\u5de5\u4f5c\u533a\u3002',
    actions: QUALITY_CAPABILITY_ACTIONS.change_control,
    accessAnyPermissions: buildAnyPermissions('change_control', QUALITY_CAPABILITY_ACTIONS.change_control),
  }),
  Object.freeze({
    key: 'equipment',
    path: `${QUALITY_SYSTEM_ROOT_PATH}/equipment`,
    title: '\u8bbe\u5907\u4e0e\u8ba1\u91cf',
    owner: 'WS05',
    resource: 'equipment_lifecycle / metrology / maintenance',
    summary: '\u8bbe\u5907\u53f0\u8d26\u3001\u8ba1\u91cf\u4e0e\u7ef4\u62a4\u4fdd\u517b\u5de5\u4f5c\u533a\u3002',
    actions: Object.freeze([
      ...QUALITY_CAPABILITY_ACTIONS.equipment_lifecycle,
      ...QUALITY_CAPABILITY_ACTIONS.metrology,
      ...QUALITY_CAPABILITY_ACTIONS.maintenance,
    ]),
    accessAnyPermissions: Object.freeze([
      ...buildAnyPermissions('equipment_lifecycle', QUALITY_CAPABILITY_ACTIONS.equipment_lifecycle),
      ...buildAnyPermissions('metrology', QUALITY_CAPABILITY_ACTIONS.metrology),
      ...buildAnyPermissions('maintenance', QUALITY_CAPABILITY_ACTIONS.maintenance),
    ]),
  }),
  Object.freeze({
    key: 'batch-records',
    path: `${QUALITY_SYSTEM_ROOT_PATH}/batch-records`,
    title: '\u6279\u8bb0\u5f55\u4e0e\u7b7e\u540d',
    owner: 'WS06',
    resource: 'batch_records',
    summary: '\u6279\u8bb0\u5f55\u6a21\u677f\u3001\u6267\u884c\u3001\u7b7e\u540d\u4e0e\u5bfc\u51fa\u5de5\u4f5c\u533a\u3002\u5982\u672a\u5b8c\u6210\u524d\u7f6e\u80fd\u529b\uff0c\u9875\u9762\u4f1a\u660e\u786e\u963b\u65ad\u8bf4\u660e\u3002',
    actions: QUALITY_CAPABILITY_ACTIONS.batch_records,
    accessAnyPermissions: buildAnyPermissions('batch_records', QUALITY_CAPABILITY_ACTIONS.batch_records),
  }),
  Object.freeze({
    key: 'audit',
    path: `${QUALITY_SYSTEM_ROOT_PATH}/audit`,
    title: '\u5ba1\u8ba1\u4e0e\u8bc1\u636e',
    owner: 'WS07',
    resource: 'audit_events',
    summary: '\u8d28\u91cf\u5ba1\u8ba1\u4e8b\u4ef6\u67e5\u770b\u3001\u8bc1\u636e\u5bfc\u51fa\u4e0e\u68c0\u7d22\u5165\u53e3\u3002',
    actions: QUALITY_CAPABILITY_ACTIONS.audit_events,
    accessAnyPermissions: buildAnyPermissions('audit_events', QUALITY_CAPABILITY_ACTIONS.audit_events),
  }),
  Object.freeze({
    key: 'governance-closure',
    path: `${QUALITY_SYSTEM_ROOT_PATH}/governance-closure`,
    title: '\u6295\u8bc9\u4e0e\u6cbb\u7406\u95ed\u73af',
    owner: 'WS08',
    resource: 'complaints / capa / internal_audit / management_review',
    summary: '\u6295\u8bc9\u3001CAPA\u3001\u5185\u5ba1\u4e0e\u7ba1\u7406\u8bc4\u5ba1\u7b49\u6cbb\u7406\u95ed\u73af\u5de5\u4f5c\u533a\uff08\u7ba1\u7406\u5165\u53e3\uff09\u3002',
    actions: Object.freeze([
      ...QUALITY_CAPABILITY_ACTIONS.complaints,
      ...QUALITY_CAPABILITY_ACTIONS.capa,
      ...QUALITY_CAPABILITY_ACTIONS.internal_audit,
      ...QUALITY_CAPABILITY_ACTIONS.management_review,
    ]),
    accessPermission: freezePermission('quality_system', 'manage'),
  }),
]);
