/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import MainLayout from './components/layout/MainLayout';
import { AuthProvider, RequireAdmin } from './lib/auth';
import { Dashboard } from './pages/Dashboard';
import { Login } from './pages/Login';
import { Teachers } from './pages/Teachers';
import { Students } from './pages/Students';
import { Admins } from './pages/Admins';
import { Classes } from './pages/Classes';
import { Exams } from './pages/Exams';
import { Documents } from './pages/Documents';
import { Appearance } from './pages/Appearance';
import { Chat } from './pages/Chat';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<RequireAdmin />}>
            <Route path="/" element={<MainLayout />}>
              <Route index element={<Dashboard />} />
              <Route path="analytics" element={<Analytics />} />
              <Route path="teachers" element={<Teachers />} />
              <Route path="students" element={<Students />} />
              <Route path="admins" element={<Admins />} />
              <Route path="classes" element={<Classes />} />
              <Route path="exams" element={<Exams />} />
              <Route path="documents" element={<Documents />} />
              <Route path="appearance" element={<Appearance />} />
              <Route path="chat" element={<Chat />} />
              <Route path="settings" element={<Settings />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}
