/**
 * app.routes.jsx — single source of truth for all routes.
 * Uses createBrowserRouter (React Router v6+).
 *
 * Note: socket is imported here and passed as a prop to ChatPage
 * so the socket singleton never bleeds into feature components directly.
 */
import { createBrowserRouter, Navigate } from 'react-router-dom';
import MainLayout from '../shared/MainLayout';
import Landing from '../features/landing/pages/Landing';
import { Dashboard } from '../features/dashboard/pages/Dashboard';
import { ChatPage } from '../features/chat/pages/ChatPage';
import { socket } from './socket';

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Landing />,
  },
  {
    element: <MainLayout />,
    children: [
      {
        index: true,
        path: 'dashboard',
        element: <Dashboard />,
      },
      {
        path: 'chat',
        element: <ChatPage socket={socket} />,
      },
      // Default redirect: bare /app → /dashboard (fallback)
      {
        path: '*',
        element: <Navigate to="/dashboard" replace />,
      },
    ],
  },
]);
