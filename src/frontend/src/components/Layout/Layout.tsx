import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
    AppBar,
    Toolbar,
    Typography,
    Button,
    Container,
    Box,
} from '@mui/material';

interface LayoutProps {
    children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
    const navigate = useNavigate();

    const handleLogout = () => {
        localStorage.removeItem('token');
        navigate('/login');
    };

    const handleNavigateLibrary = () => {
        navigate('/library');
    };

    const handleNavigateCollections = () => {
        navigate('/collections');
    };

    return (
        <Box sx={{ display: 'flex', flexDirection: 'column', minHeight: '100vh' }}>
            <AppBar position="static">
                <Toolbar>
                    <Typography variant="h6" sx={{ flexGrow: 1 }}>
                        📚 PDF Library Manager
                    </Typography>
                    <Button color="inherit" onClick={handleNavigateLibrary}>
                        Library
                    </Button>
                    <Button color="inherit" onClick={handleNavigateCollections}>
                        Collections
                    </Button>
                    <Button color="inherit" onClick={handleLogout}>
                        Logout
                    </Button>
                </Toolbar>
            </AppBar>
            <Container maxWidth="lg" sx={{ py: 4, flex: 1 }}>
                {children}
            </Container>
        </Box>
    );
};

export default Layout;
