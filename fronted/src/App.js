import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import Layout from './components/Layout';
import PermissionGuard from './components/PermissionGuard';
import FeatureVisibilityGuard from './components/FeatureVisibilityGuard';
import SuperAdminGuard from './components/SuperAdminGuard';

const LoginPage = lazy(() => import('./pages/LoginPage'));
const Dashboard = lazy(() => import('./pages/Dashboard'));
const UserManagement = lazy(() => import('./pages/UserManagement'));
const KnowledgeUpload = lazy(() => import('./pages/KnowledgeUpload'));
const DocumentBrowser = lazy(() => import('./pages/DocumentBrowser'));
const DocumentReviewAudit = lazy(() => import('./pages/DocumentReviewAudit'));
const Chat = lazy(() => import('./pages/Chat'));
const Agents = lazy(() => import('./pages/Agents'));
const PermissionGroupManagement = lazy(() => import('./pages/PermissionGroupManagement'));
const DataSecurity = lazy(() => import('./pages/DataSecurity'));
const DataSecurityTest = lazy(() => import('./pages/DataSecurity-test'));
const OrgDirectoryManagement = lazy(() => import('./pages/OrgDirectoryManagement'));
const Unauthorized = lazy(() => import('./pages/Unauthorized'));
const ChangePassword = lazy(() => import('./pages/ChangePassword'));
const AuditLogs = lazy(() => import('./pages/AuditLogs'));
const Tools = lazy(() => import('./pages/Tools'));
const PatentDownload = lazy(() => import('./pages/PatentDownload'));
const PaperDownload = lazy(() => import('./pages/PaperDownload'));
const PaperWorkspace = lazy(() => import('./pages/PaperWorkspace'));
const CollectionWorkbench = lazy(() => import('./pages/CollectionWorkbench'));
const KnowledgeBases = lazy(() => import('./pages/KnowledgeBases'));
const NasBrowser = lazy(() => import('./pages/NasBrowser'));
const DrugAdminNavigator = lazy(() => import('./pages/DrugAdminNavigator'));
const NMPATool = lazy(() => import('./pages/NMPATool'));
const SearchConfigsPanel = lazy(() => import('./pages/SearchConfigsPanel'));
const ChatConfigsPanel = lazy(() => import('./pages/ChatConfigsPanel'));
const DocumentReview = lazy(() => import('./pages/DocumentReview'));
const DocumentAudit = lazy(() => import('./pages/DocumentAudit'));
const SuperAdminFeatureVisibility = lazy(() => import('./pages/SuperAdminFeatureVisibility'));


function RouteLoadingFallback() {
  return <div style={{ padding: 16 }}>Loading...</div>;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<RouteLoadingFallback />}>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <PermissionGuard>
                  <Layout>
                    <Navigate to="/chat" replace />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/dashboard"
              element={
                <PermissionGuard>
                  <Layout>
                    <Dashboard />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/users"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <Layout>
                    <UserManagement />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/upload"
              element={
                <PermissionGuard>
                  <Layout>
                    <KnowledgeUpload />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/documents"
              element={
                <PermissionGuard>
                  <Layout>
                    <DocumentReviewAudit />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/documents/review"
              element={
                <PermissionGuard>
                  <Layout>
                    <DocumentReview />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/documents/audit"
              element={
                <PermissionGuard>
                  <Layout>
                    <DocumentAudit />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/browser"
              element={
                <PermissionGuard>
                  <Layout>
                    <DocumentBrowser />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/chat"
              element={
                <PermissionGuard>
                  <Layout>
                    <Chat />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/agents"
              element={
                <PermissionGuard>
                  <Layout>
                    <Agents />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/change-password"
              element={
                <PermissionGuard>
                  <Layout>
                    <ChangePassword />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/tools"
              element={
                <PermissionGuard>
                  <Layout>
                    <Tools />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/tools/patent-download"
              element={
                <PermissionGuard>
                  <Layout>
                    <PatentDownload />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/tools/paper-download"
              element={
                <PermissionGuard>
                  <Layout>
                    <PaperDownload />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/tools/paper-workspace"
              element={
                <PermissionGuard>
                  <Layout>
                    <PaperWorkspace />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/tools/collection-workbench"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <Layout>
                    <CollectionWorkbench />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/tools/nas-browser"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <FeatureVisibilityGuard flagKey="tool_nas_visible">
                    <Layout>
                      <NasBrowser />
                    </Layout>
                  </FeatureVisibilityGuard>
                </PermissionGuard>
              }
            />
            <Route
              path="/tools/drug-admin"
              element={
                <PermissionGuard>
                  <FeatureVisibilityGuard flagKey="tool_drug_admin_visible">
                    <Layout>
                      <DrugAdminNavigator />
                    </Layout>
                  </FeatureVisibilityGuard>
                </PermissionGuard>
              }
            />
            <Route
              path="/tools/nmpa"
              element={
                <PermissionGuard>
                  <FeatureVisibilityGuard flagKey="tool_nmpa_visible">
                    <Layout>
                      <NMPATool />
                    </Layout>
                  </FeatureVisibilityGuard>
                </PermissionGuard>
              }
            />
            <Route
              path="/kbs"
              element={
                <PermissionGuard>
                  <Layout>
                    <KnowledgeBases />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/chat-configs"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <Layout>
                    <ChatConfigsPanel />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/search-configs"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <Layout>
                    <SearchConfigsPanel />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/audit"
              element={
                <PermissionGuard>
                  <Navigate to="/documents?tab=records" replace />
                </PermissionGuard>
              }
            />
            <Route
              path="/permission-groups"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <Layout>
                    <PermissionGroupManagement />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/org-directory"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <Layout>
                    <OrgDirectoryManagement />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/data-security"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <Layout>
                    <DataSecurity />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route
              path="/data-security-test"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <FeatureVisibilityGuard flagKey="page_data_security_test_visible">
                    <Layout>
                      <DataSecurityTest />
                    </Layout>
                  </FeatureVisibilityGuard>
                </PermissionGuard>
              }
            />
            <Route
              path="/logs"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <FeatureVisibilityGuard flagKey="page_logs_visible">
                    <Layout>
                      <AuditLogs />
                    </Layout>
                  </FeatureVisibilityGuard>
                </PermissionGuard>
              }
            />
            <Route
              path="/super-admin/features"
              element={
                <PermissionGuard allowedRoles={['admin']}>
                  <SuperAdminGuard>
                    <Layout>
                      <SuperAdminFeatureVisibility />
                    </Layout>
                  </SuperAdminGuard>
                </PermissionGuard>
              }
            />
            <Route
              path="/unauthorized"
              element={
                <PermissionGuard>
                  <Layout>
                    <Unauthorized />
                  </Layout>
                </PermissionGuard>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
