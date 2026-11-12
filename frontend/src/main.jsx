import React from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider } from 'react-router-dom';
import { RouteFailure } from './RouteFailure';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './styles.css';
import './worldclass.css';
import './site/redesign.css';
import './workspace.css';
const element = document.getElementById('root');
if (!element)
    throw new Error('Missing root');
const router = createBrowserRouter([{
  path: '/*', element: <App />, errorElement: <RouteFailure />
}]);
createRoot(element).render(<React.StrictMode>
    <QueryClientProvider client={new QueryClient()}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </React.StrictMode>);
if ('serviceWorker' in navigator && import.meta.env.PROD) {
    window.addEventListener('load', () => navigator.serviceWorker.register('/sw.js').catch(() => { }));
}
