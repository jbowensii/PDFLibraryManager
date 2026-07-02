import React, { useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline, CircularProgress, Box } from '@mui/material';
import Layout from './components/Layout/Layout';
import LoginPage from './pages/LoginPage';
import LibraryPage from './pages/LibraryPage';
import BookDetailPage from './pages/BookDetailPage';
import CollectionsPage from './pages/CollectionsPage';
import AdminPanel from './pages/AdminPanel';
import APIClient from './api/client';

// Theme configuration
const theme = createTheme({
    palette: {
        primary: {
            main: '#1976d2',
        },
        secondary: {
            main: '#dc004e',
        },
    },
});

interface ProtectedRouteProps {
    children: React.ReactNode;
}

// Protected route that checks for authentication
const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
    const [isAuthenticated, setIsAuthenticated] = useState<boolean | null>(null);

    useEffect(() => {
        const checkAuth = async () => {
            const token = localStorage.getItem('access_token');
            if (!token) {
                setIsAuthenticated(false);
                return;
            }

            try {
                await APIClient.getCurrentUser();
                setIsAuthenticated(true);
            } catch {
                localStorage.removeItem('access_token');
                setIsAuthenticated(false);
            }
        };

        checkAuth();
    }, []);

    if (isAuthenticated === null) {
        return (
            <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh' }}>
                <CircularProgress />
            </Box>
        );
    }

    return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />;
};

const App: React.FC = () => {
    return (
        <ThemeProvider theme={theme}>
            <CssBaseline />
            <BrowserRouter>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route
                        path="/*"
                        element={
                            <ProtectedRoute>
                                <Layout>
                                    <Routes>
                                        <Route path="/" element={<Navigate to="/library" replace />} />
                                        <Route path="/library" element={<LibraryPage />} />
                                        <Route path="/books/:id" element={<BookDetailPage />} />
                                        <Route path="/collections" element={<CollectionsPage />} />
                                        <Route path="/collections/:collectionId" element={<CollectionsPage />} />
                                        <Route path="/admin" element={<AdminPanel />} />
                                    </Routes>
                                </Layout>
                            </ProtectedRoute>
                        }
                    />
                </Routes>
            </BrowserRouter>
        </ThemeProvider>
    );
};

export default App;
