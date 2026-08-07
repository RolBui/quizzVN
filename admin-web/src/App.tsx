/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import type { ReactNode } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import MainLayout from './components/layout/MainLayout';
import {
  type AdminPermissionKey,
  useAdminPermissions,
} from './lib/admin-permissions';
import { AuthProvider, RequireAdmin, useAuth } from './lib/auth';
import { Dashboard } from './pages/Dashboard';
import { Login } from './pages/Login';
import { SetPassword } from './pages/SetPassword';
import { Teachers } from './pages/Teachers';
import { Students } from './pages/Students';
import { Admins } from './pages/Admins';
import { Classes } from './pages/Classes';
import { Exams } from './pages/Exams';
import { ExamCreate } from './pages/ExamCreate';
import { ExamAICreate } from './pages/ExamAICreate';
import { ExamTextCreate } from './pages/ExamTextCreate';
import { Documents } from './pages/Documents';
import { Chat } from './pages/Chat';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';

function RequireAdminPermission({
  children,
  permission,
}: {
  children: ReactNode;
  permission: AdminPermissionKey;
}) {
  const { user } = useAuth();
  const permissions = useAdminPermissions(user);

  if (!permissions.includes(permission)) {
    return <Navigate to="/" replace />;
  }

  return <>{children}</>;
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/set-password" element={<SetPassword />} />
          <Route element={<RequireAdmin />}>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="analytics" element={<Analytics />} />
              <Route
                path="teachers"
                element={
                  <RequireAdminPermission permission="teachers">
                    <Teachers />
                  </RequireAdminPermission>
                }
              />
              <Route
                path="students"
                element={
                  <RequireAdminPermission permission="students">
                    <Students />
                  </RequireAdminPermission>
                }
              />
              <Route
                path="admins"
                element={
                  <RequireAdminPermission permission="admins">
                    <Admins />
                  </RequireAdminPermission>
                }
              />
              <Route
                path="classes"
                element={
                  <RequireAdminPermission permission="classes">
                    <Classes />
                  </RequireAdminPermission>
                }
              />
              <Route
                path="exams"
                element={
                  <RequireAdminPermission permission="exams">
                    <Exams />
                  </RequireAdminPermission>
                }
              />
              <Route
                path="exams/new"
                element={
                  <RequireAdminPermission permission="exams">
                    <ExamCreate />
                  </RequireAdminPermission>
                }
              />
              <Route
                path="exams/edit/:id"
                element={
                  <RequireAdminPermission permission="exams">
                    <ExamCreate />
                  </RequireAdminPermission>
                }
              />
              <Route
                path="exams/text"
                element={
                  <RequireAdminPermission permission="exams">
                    <ExamTextCreate />
                  </RequireAdminPermission>
                }
              />
              <Route
                path="exams/ai"
                element={
                  <RequireAdminPermission permission="exams">
                    <ExamAICreate />
                  </RequireAdminPermission>
                }
              />
              <Route
                path="documents"
                element={
                  <RequireAdminPermission permission="documents">
                    <Documents />
                  </RequireAdminPermission>
                }
              />
              <Route path="chat" element={<Chat />} />
              <Route path="settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Route>
        </Routes>
        <ToastContainer
          position="top-right"
          autoClose={3000}
          hideProgressBar={false}
          newestOnTop
          closeOnClick
          pauseOnFocusLoss
          draggable
          pauseOnHover
          theme="light"
        />
      </AuthProvider>
    </BrowserRouter>
  );
}
