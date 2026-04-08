import React, { Suspense } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './hooks/useAuth';
import Layout from './components/Layout';
import PermissionGuard from './components/PermissionGuard';
import { getDefaultLandingRoute } from './features/auth/defaultLandingRoute';
import { APP_ROUTES } from './routes/routeRegistry';

function RouteLoadingFallback() {
  return <div style={{ padding: 16 }}>加载中...</div>;
}

function DefaultRouteRedirect() {
  const { user } = useAuth();

  return <Navigate to={getDefaultLandingRoute(user)} replace />;
}

function renderRouteElement(route) {
  const PageComponent = route.component;
  if (route.public) {
    return <PageComponent />;
  }

  return (
    <PermissionGuard
      allowedRoles={route.guard?.allowedRoles}
      permission={route.guard?.permission}
      permissions={route.guard?.permissions}
      anyPermissions={route.guard?.anyPermissions}
    >
      <Layout>
        <PageComponent />
      </Layout>
    </PermissionGuard>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<RouteLoadingFallback />}>
          <Routes>
            <Route
              path="/"
              element={(
                <PermissionGuard>
                  <Layout>
                    <DefaultRouteRedirect />
                  </Layout>
                </PermissionGuard>
              )}
            />
            {APP_ROUTES.map((route) => (
              <Route key={route.path} path={route.path} element={renderRouteElement(route)} />
            ))}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
