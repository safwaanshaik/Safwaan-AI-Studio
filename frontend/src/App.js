import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Provider } from 'react-redux';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import { Toaster } from 'react-hot-toast';

// Components
import Dashboard from './pages/Dashboard';
import ContentStudio from './routes/ContentStudio';
import WorkflowStudio from './routes/WorkflowStudio';
import VideoGalleryPage from './pages/VideoGalleryPage';
import Layout from './components/Layout';
import Login from './components/auth/Login';
import Register from './components/auth/Register';
import ProtectedRoute from './components/auth/ProtectedRoute';

// Workflow Components
import WorkflowBuilder from './components/workflow/WorkflowBuilder';

// Context
import { AuthProvider } from './context/AuthContext';

// Store
import store from './store';

// Theme
const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#06b6d4',
    },
    secondary: {
      main: '#a855f7',
    },
    background: {
      default: '#0b0f19',
      paper: 'rgba(15, 23, 42, 0.8)',
    },
  },
  typography: {
    fontFamily: 'Inter, sans-serif',
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          scrollbarWidth: 'thin',
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'rgba(148, 163, 184, 0.3)',
            borderRadius: '4px',
          },
          '&::-webkit-scrollbar-thumb:hover': {
            background: 'rgba(148, 163, 184, 0.5)',
          },
        },
      },
    },
  },
});

// Query Client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // 5 minutes
      cacheTime: 1000 * 60 * 10, // 10 minutes
    },
  },
});

function App() {
  return (
    <Provider store={store}>
      <QueryClientProvider client={queryClient}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <AuthProvider>
            <Router>
              <div className="App">
                <Routes>
                  {/* Public Routes */}
                  <Route path="/login" element={<Login />} />
                  <Route path="/register" element={<Register />} />

                  {/* Protected Routes */}
                  <Route path="/" element={
                    <ProtectedRoute>
                      <Layout />
                    </ProtectedRoute>
                  }>
                    <Route index element={<Dashboard />} />
                    <Route path="dashboard" element={<Dashboard />} />
                    <Route path="studio" element={<ContentStudio />} />
                    <Route path="workflow" element={<WorkflowStudio />} />
                    <Route path="workflow/builder" element={<WorkflowBuilder />} />
                    <Route path="videos" element={<VideoGalleryPage />} />
                  </Route>
                </Routes>
              </div>
            </Router>
            <Toaster
              position="top-right"
              toastOptions={{
                duration: 4000,
                style: {
                  background: 'rgba(15, 23, 42, 0.9)',
                  color: '#e2e8f0',
                  border: '1px solid rgba(148, 163, 184, 0.2)',
                  backdropFilter: 'blur(16px)',
                },
              }}
            />
          </AuthProvider>
        </ThemeProvider>
      </QueryClientProvider>
    </Provider>
  );
}

export default App;