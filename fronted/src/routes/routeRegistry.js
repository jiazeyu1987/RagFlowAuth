import { lazy } from 'react';
import { QUALITY_SYSTEM_ROUTE_PERMISSION } from '../shared/auth/capabilities';
import { QUALITY_SYSTEM_MODULES, QUALITY_SYSTEM_ROOT_PATH } from '../features/qualitySystem/moduleCatalog';

export const ROUTE_TEXT = {
  home: '\u9996\u9875',
  nav: {
    chat: '\u667a\u80fd\u5bf9\u8bdd',
    agents: '\u5168\u5e93\u641c\u7d22',
    kbs: '\u77e5\u8bc6\u5e93\u914d\u7f6e',
    browser: '\u6587\u6863\u6d4f\u89c8',
    documentHistory: '\u6587\u6863\u8bb0\u5f55',
    upload: '\u6587\u6863\u4e0a\u4f20',
    approvalCenter: '\u5ba1\u6279\u4e2d\u5fc3',
    approvalConfig: '\u5ba1\u6279\u914d\u7f6e',
    inbox: '\u7ad9\u5185\u4fe1',
    changePassword: '\u4fee\u6539\u5bc6\u7801',
    tools: '\u5b9e\u7528\u5de5\u5177',
    users: '\u7528\u6237\u7ba1\u7406',
    orgDirectory: '\u7ec4\u7ec7\u7ba1\u7406',
    permissionGroups: '\u6743\u9650\u5206\u7ec4',
    dataSecurity: '\u6570\u636e\u5b89\u5168',
    logs: '\u65e5\u5fd7\u5ba1\u8ba1',
    notificationSettings: '\u901a\u77e5\u8bbe\u7f6e',
    electronicSignatures: '\u7535\u5b50\u7b7e\u540d',
    trainingCompliance: '\u57f9\u8bad\u5408\u89c4',
    qualitySystem: '\u4f53\u7cfb\u6587\u4ef6',
  },
  toolTitles: {
    patentDownload: '\u4e13\u5229\u4e0b\u8f7d',
    paperDownload: '\u8bba\u6587\u4e0b\u8f7d',
    nasBrowser: 'NAS\u4e91\u76d8',
    drugAdmin: '\u836f\u76d1\u5bfc\u822a',
    packageDrawing: '\u5305\u88c5\u56fe\u7eb8',
  },
};

const LoginPage = lazy(() => import('../pages/LoginPage'));
const Dashboard = lazy(() => import('../pages/Dashboard'));
const UserManagement = lazy(() => import('../pages/UserManagement'));
const KnowledgeUpload = lazy(() => import('../pages/KnowledgeUpload'));
const DocumentBrowser = lazy(() => import('../pages/DocumentBrowser'));
const Chat = lazy(() => import('../pages/Chat'));
const Agents = lazy(() => import('../pages/Agents'));
const PermissionGroupManagement = lazy(() => import('../pages/PermissionGroupManagement'));
const DataSecurity = lazy(() => import('../pages/DataSecurity'));
const NotificationSettings = lazy(() => import('../pages/NotificationSettings'));
const ApprovalCenter = lazy(() => import('../pages/ApprovalCenter'));
const ApprovalConfig = lazy(() => import('../pages/ApprovalConfig'));
const ElectronicSignatureManagement = lazy(() => import('../pages/ElectronicSignatureManagement'));
const TrainingComplianceManagement = lazy(() => import('../pages/TrainingComplianceManagement'));
const InboxPage = lazy(() => import('../pages/InboxPage'));
const OrgDirectoryManagement = lazy(() => import('../pages/OrgDirectoryManagement'));
const Unauthorized = lazy(() => import('../pages/Unauthorized'));
const ChangePassword = lazy(() => import('../pages/ChangePassword'));
const AuditLogs = lazy(() => import('../pages/AuditLogs'));
const Tools = lazy(() => import('../pages/Tools'));
const PatentDownload = lazy(() => import('../pages/PatentDownload'));
const PaperDownload = lazy(() => import('../pages/PaperDownload'));
const KnowledgeBases = lazy(() => import('../pages/KnowledgeBases'));
const NasBrowser = lazy(() => import('../pages/NasBrowser'));
const DrugAdminNavigator = lazy(() => import('../pages/DrugAdminNavigator'));
const NMPATool = lazy(() => import('../pages/NMPATool'));
const PackageDrawingTool = lazy(() => import('../pages/PackageDrawingTool'));
const SearchConfigsPanel = lazy(() => import('../pages/SearchConfigsPanel'));
const ChatConfigsPanel = lazy(() => import('../pages/ChatConfigsPanel'));
const DocumentAudit = lazy(() => import('../pages/DocumentAudit'));
const QualitySystem = lazy(() => import('../pages/QualitySystem'));

export const APP_ROUTES = [
  { path: '/login', component: LoginPage, public: true },
  { path: '/dashboard', component: Dashboard, title: ROUTE_TEXT.home },
  {
    path: '/users',
    component: UserManagement,
    title: ROUTE_TEXT.nav.users,
    showInNav: true,
    icon: '\ud83d\udc65',
    guard: { allowedRoles: ['admin', 'sub_admin'] },
  },
  {
    path: '/upload',
    component: KnowledgeUpload,
    title: ROUTE_TEXT.nav.upload,
    showInNav: true,
    icon: '\ud83d\udce4',
    guard: { permission: { resource: 'kb_documents', action: 'upload' } },
    navHiddenRoles: ['admin'],
  },
  {
    path: '/document-history',
    component: DocumentAudit,
    title: ROUTE_TEXT.nav.documentHistory,
    showInNav: true,
    icon: '\ud83d\uddc2\ufe0f',
    guard: {
      anyPermissions: [
        { resource: 'kb_documents', action: 'review' },
        { resource: 'kb_documents', action: 'view' },
      ],
    },
  },
  {
    path: '/browser',
    component: DocumentBrowser,
    title: ROUTE_TEXT.nav.browser,
    showInNav: true,
    icon: '\ud83d\udcc4',
    navHiddenRoles: ['admin'],
  },
  {
    path: '/chat',
    component: Chat,
    title: ROUTE_TEXT.nav.chat,
    showInNav: true,
    icon: '\ud83d\udcac',
    navHiddenRoles: ['admin'],
  },
  {
    path: '/agents',
    component: Agents,
    title: ROUTE_TEXT.nav.agents,
    showInNav: true,
    icon: '\ud83d\udd0d',
    navHiddenRoles: ['admin'],
  },
  {
    path: '/change-password',
    component: ChangePassword,
    title: ROUTE_TEXT.nav.changePassword,
    showInNav: true,
    icon: '\ud83d\udd11',
  },
  {
    path: '/tools',
    component: Tools,
    title: ROUTE_TEXT.nav.tools,
    showInNav: true,
    icon: '\ud83e\uddf0',
    guard: { permission: { resource: 'tools', action: 'view' } },
    navHiddenRoles: ['admin'],
    matchPrefixes: ['/tools/'],
  },
  {
    path: '/tools/patent-download',
    component: PatentDownload,
    title: ROUTE_TEXT.toolTitles.patentDownload,
    guard: { permission: { resource: 'tools', action: 'view', target: 'patent_download' } },
  },
  {
    path: '/tools/paper-download',
    component: PaperDownload,
    title: ROUTE_TEXT.toolTitles.paperDownload,
    guard: { permission: { resource: 'tools', action: 'view', target: 'paper_download' } },
  },
  {
    path: '/tools/nas-browser',
    component: NasBrowser,
    title: ROUTE_TEXT.toolTitles.nasBrowser,
    guard: {
      allowedRoles: ['admin'],
      permission: { resource: 'tools', action: 'view', target: 'nas_browser' },
    },
  },
  {
    path: '/tools/drug-admin',
    component: DrugAdminNavigator,
    title: ROUTE_TEXT.toolTitles.drugAdmin,
    guard: { permission: { resource: 'tools', action: 'view', target: 'drug_admin' } },
  },
  {
    path: '/tools/nmpa',
    component: NMPATool,
    title: 'NMPA',
    guard: { permission: { resource: 'tools', action: 'view', target: 'nmpa' } },
  },
  {
    path: '/tools/package-drawing',
    component: PackageDrawingTool,
    title: ROUTE_TEXT.toolTitles.packageDrawing,
    guard: { permission: { resource: 'tools', action: 'view', target: 'package_drawing' } },
  },
  {
    path: '/kbs',
    component: KnowledgeBases,
    title: ROUTE_TEXT.nav.kbs,
    showInNav: true,
    icon: '\ud83d\udcd6',
    guard: {
      allowedRoles: ['sub_admin'],
      permission: { resource: 'kbs_config', action: 'view' },
    },
    navHiddenRoles: ['admin'],
  },
  {
    path: '/chat-configs',
    component: ChatConfigsPanel,
    title: ROUTE_TEXT.home,
    guard: {
      allowedRoles: ['sub_admin'],
      permission: { resource: 'kbs_config', action: 'view' },
    },
  },
  {
    path: '/search-configs',
    component: SearchConfigsPanel,
    title: ROUTE_TEXT.home,
    guard: { allowedRoles: ['admin'] },
  },
  {
    path: '/permission-groups',
    component: PermissionGroupManagement,
    title: ROUTE_TEXT.nav.permissionGroups,
    showInNav: true,
    icon: '\ud83d\udee1\ufe0f',
    guard: { allowedRoles: ['sub_admin'] },
  },
  {
    path: '/approvals',
    component: ApprovalCenter,
    title: ROUTE_TEXT.nav.approvalCenter,
    showInNav: true,
    icon: '\ud83d\udccb',
  },
  {
    path: '/approval-config',
    component: ApprovalConfig,
    title: ROUTE_TEXT.nav.approvalConfig,
    showInNav: true,
    icon: '\ud83d\udd27',
    guard: { allowedRoles: ['admin'] },
  },
  {
    path: '/inbox',
    component: InboxPage,
    title: ROUTE_TEXT.nav.inbox,
    showInNav: true,
    icon: '\ud83d\udcec',
  },
  {
    path: '/org-directory',
    component: OrgDirectoryManagement,
    title: ROUTE_TEXT.nav.orgDirectory,
    showInNav: true,
    icon: '\ud83c\udfe2',
    guard: { allowedRoles: ['admin'] },
  },
  {
    path: '/data-security',
    component: DataSecurity,
    title: ROUTE_TEXT.nav.dataSecurity,
    showInNav: true,
    icon: '\ud83d\udd12',
    guard: { allowedRoles: ['admin', 'sub_admin'] },
    navGuard: { allowedRoles: ['admin'] },
  },
  {
    path: '/notification-settings',
    component: NotificationSettings,
    title: ROUTE_TEXT.nav.notificationSettings,
    showInNav: true,
    icon: '\ud83d\udd14',
    guard: { allowedRoles: ['admin'] },
  },
  {
    path: '/electronic-signatures',
    component: ElectronicSignatureManagement,
    title: ROUTE_TEXT.nav.electronicSignatures,
    showInNav: true,
    icon: '\u270d\ufe0f',
    guard: { allowedRoles: ['admin'] },
  },
  {
    path: '/training-compliance',
    component: TrainingComplianceManagement,
    title: ROUTE_TEXT.nav.trainingCompliance,
    showInNav: true,
    icon: '\ud83c\udf93',
    guard: { allowedRoles: ['admin'] },
  },
  {
    path: QUALITY_SYSTEM_ROOT_PATH,
    component: QualitySystem,
    title: ROUTE_TEXT.nav.qualitySystem,
    showInNav: true,
    icon: '\ud83e\uddea',
    guard: { permission: QUALITY_SYSTEM_ROUTE_PERMISSION },
    navGuard: { allowedRoles: ['admin', 'sub_admin'] },
    matchPrefixes: [`${QUALITY_SYSTEM_ROOT_PATH}/`],
  },
  ...QUALITY_SYSTEM_MODULES.map((module) => ({
    path: module.path,
    component: QualitySystem,
    title: module.title,
    guard: { permission: QUALITY_SYSTEM_ROUTE_PERMISSION },
  })),
  {
    path: '/messages',
    component: InboxPage,
    title: ROUTE_TEXT.nav.inbox,
  },
  {
    path: '/logs',
    component: AuditLogs,
    title: ROUTE_TEXT.nav.logs,
    showInNav: true,
    icon: '\ud83d\udccb',
    guard: { allowedRoles: ['admin'] },
  },
  {
    path: '/unauthorized',
    component: Unauthorized,
    title: ROUTE_TEXT.home,
  },
];

export const NAVIGATION_ROUTES = APP_ROUTES.filter((route) => route.showInNav);

export const findRouteConfig = (pathname) => APP_ROUTES.find((route) => route.path === pathname) || null;

export const getRouteTitle = (pathname) => findRouteConfig(pathname)?.title || ROUTE_TEXT.home;
