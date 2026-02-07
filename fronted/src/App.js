import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './hooks/useAuth';
import LoginPage from './pages/LoginPage';
import Layout from './components/Layout';
import UserManagement from './pages/UserManagement';
import KnowledgeUpload from './pages/KnowledgeUpload';
import DocumentBrowser from './pages/DocumentBrowser';
import DocumentReviewAudit from './pages/DocumentReviewAudit';
import Chat from './pages/Chat';
import Agents from './pages/Agents';
import PermissionGroupManagement from './pages/PermissionGroupManagement';
import DataSecurity from './pages/DataSecurity';
import OrgDirectoryManagement from './pages/OrgDirectoryManagement';
import Unauthorized from './pages/Unauthorized';
import PermissionGuard from './components/PermissionGuard';
import ChangePassword from './pages/ChangePassword';
import AuditLogs from './pages/AuditLogs';
import Tools from './pages/Tools';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
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
            path="/logs"
            element={
              <PermissionGuard allowedRoles={['admin']}>
                <Layout>
                  <AuditLogs />
                </Layout>
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
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
