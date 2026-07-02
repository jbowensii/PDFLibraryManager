import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Container,
    Card,
    TextField,
    Button,
    Box,
    Alert,
    CircularProgress,
    Typography,
} from '@mui/material';
import APIClient from '../api/client';

const LoginPage: React.FC = () => {
    const navigate = useNavigate();
    const [showRegister, setShowRegister] = useState(false);

    // Login state
    const [loginUsername, setLoginUsername] = useState('');
    const [loginPassword, setLoginPassword] = useState('');
    const [loginLoading, setLoginLoading] = useState(false);
    const [loginError, setLoginError] = useState('');

    // Register state
    const [registerUsername, setRegisterUsername] = useState('');
    const [registerEmail, setRegisterEmail] = useState('');
    const [registerPassword, setRegisterPassword] = useState('');
    const [registerLoading, setRegisterLoading] = useState(false);
    const [registerError, setRegisterError] = useState('');

    const handleLogin = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoginError('');
        setLoginLoading(true);

        try {
            const response = await APIClient.login(loginUsername, loginPassword);
            localStorage.setItem('access_token', response.access_token);
            navigate('/library');
        } catch (error: any) {
            setLoginError(error.response?.data?.detail || 'Login failed');
        } finally {
            setLoginLoading(false);
        }
    };

    const handleRegister = async (e: React.FormEvent) => {
        e.preventDefault();
        setRegisterError('');
        setRegisterLoading(true);

        try {
            await APIClient.register(registerUsername, registerEmail, registerPassword);
            setRegisterError('');
            setShowRegister(false);
            setLoginUsername(registerUsername);
            setLoginPassword('');
            setRegisterUsername('');
            setRegisterEmail('');
            setRegisterPassword('');
        } catch (error: any) {
            setRegisterError(error.response?.data?.detail || 'Registration failed');
        } finally {
            setRegisterLoading(false);
        }
    };

    return (
        <Container maxWidth="sm">
            <Box sx={{ mt: 8, mb: 4 }}>
                <Card sx={{ p: 3 }}>
                    {!showRegister ? (
                        <Box>
                            <Typography variant="h5" sx={{ mb: 3 }}>Login</Typography>
                            <Box component="form" onSubmit={handleLogin}>
                                {loginError && <Alert severity="error" sx={{ mb: 2 }}>{loginError}</Alert>}
                                <TextField
                                    fullWidth
                                    label="Username"
                                    value={loginUsername}
                                    onChange={(e) => setLoginUsername(e.target.value)}
                                    margin="normal"
                                    disabled={loginLoading}
                                />
                                <TextField
                                    fullWidth
                                    label="Password"
                                    type="password"
                                    value={loginPassword}
                                    onChange={(e) => setLoginPassword(e.target.value)}
                                    margin="normal"
                                    disabled={loginLoading}
                                />
                                <Button
                                    fullWidth
                                    variant="contained"
                                    color="primary"
                                    type="submit"
                                    sx={{ mt: 3 }}
                                    disabled={loginLoading}
                                >
                                    {loginLoading ? <CircularProgress size={24} /> : 'Login'}
                                </Button>
                                <Box sx={{ mt: 2, textAlign: 'center' }}>
                                    <Typography variant="body2">
                                        Don't have an account?{' '}
                                        <Button
                                            size="small"
                                            onClick={() => setShowRegister(true)}
                                            sx={{ textTransform: 'none' }}
                                        >
                                            Register here
                                        </Button>
                                    </Typography>
                                </Box>
                            </Box>
                        </Box>
                    ) : (
                        <Box>
                            <Typography variant="h5" sx={{ mb: 3 }}>Register</Typography>
                            <Box component="form" onSubmit={handleRegister}>
                                {registerError && <Alert severity="error" sx={{ mb: 2 }}>{registerError}</Alert>}
                                <TextField
                                    fullWidth
                                    label="Username"
                                    value={registerUsername}
                                    onChange={(e) => setRegisterUsername(e.target.value)}
                                    margin="normal"
                                    disabled={registerLoading}
                                />
                                <TextField
                                    fullWidth
                                    label="Email"
                                    type="email"
                                    value={registerEmail}
                                    onChange={(e) => setRegisterEmail(e.target.value)}
                                    margin="normal"
                                    disabled={registerLoading}
                                />
                                <TextField
                                    fullWidth
                                    label="Password"
                                    type="password"
                                    value={registerPassword}
                                    onChange={(e) => setRegisterPassword(e.target.value)}
                                    margin="normal"
                                    disabled={registerLoading}
                                />
                                <Button
                                    fullWidth
                                    variant="contained"
                                    color="primary"
                                    type="submit"
                                    sx={{ mt: 3 }}
                                    disabled={registerLoading}
                                >
                                    {registerLoading ? <CircularProgress size={24} /> : 'Register'}
                                </Button>
                                <Box sx={{ mt: 2, textAlign: 'center' }}>
                                    <Typography variant="body2">
                                        Already have an account?{' '}
                                        <Button
                                            size="small"
                                            onClick={() => setShowRegister(false)}
                                            sx={{ textTransform: 'none' }}
                                        >
                                            Login here
                                        </Button>
                                    </Typography>
                                </Box>
                            </Box>
                        </Box>
                    )}
                </Card>
            </Box>
        </Container>
    );
};

export default LoginPage;
