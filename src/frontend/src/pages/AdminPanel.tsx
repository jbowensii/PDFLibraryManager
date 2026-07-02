import React, { useState, useEffect } from 'react';
import {
    Container,
    Tabs,
    Tab,
    Box,
    Paper,
    Button,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    CircularProgress,
    Alert,
} from '@mui/material';
import APIClient from '../api/client';

interface TabPanelProps {
    children?: React.ReactNode;
    index: number;
    value: number;
}

function CustomTabPanel(props: TabPanelProps) {
    const { children, value, index, ...other } = props;

    return (
        <div
            role="tabpanel"
            hidden={value !== index}
            id={`admin-tabpanel-${index}`}
            aria-labelledby={`admin-tab-${index}`}
            {...other}
        >
            {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
        </div>
    );
}

function a11yProps(index: number) {
    return {
        id: `admin-tab-${index}`,
        'aria-controls': `admin-tabpanel-${index}`,
    };
}

interface Duplicate {
    id: number;
    book_id_1: number;
    book_id_2: number;
    similarity_score: number;
    status: string;
}

interface User {
    id: number;
    username: string;
    email: string;
    role: string;
}

interface AuditLog {
    id: number;
    user_id?: number;
    action: string;
    created_at: string;
}

const AdminPanel: React.FC = () => {
    const [tabValue, setTabValue] = useState(0);
    const [duplicates, setDuplicates] = useState<Duplicate[]>([]);
    const [users, setUsers] = useState<User[]>([]);
    const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
    const [loading, setLoading] = useState(false);
    const [scanStatus, setScanStatus] = useState('');

    const handleTabChange = (event: React.SyntheticEvent, newValue: number) => {
        setTabValue(newValue);
    };

    useEffect(() => {
        if (tabValue === 0) loadDuplicates();
        if (tabValue === 1) loadUsers();
        if (tabValue === 2) loadAuditLog();
    }, [tabValue]);

    const loadDuplicates = async () => {
        try {
            setLoading(true);
            const response = await APIClient.listDuplicates(0, 50);
            setDuplicates(response.items);
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to load duplicates');
        } finally {
            setLoading(false);
        }
    };

    const loadUsers = async () => {
        try {
            setLoading(true);
            const response = await APIClient.listUsers(0, 50);
            setUsers(response.items);
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to load users');
        } finally {
            setLoading(false);
        }
    };

    const loadAuditLog = async () => {
        try {
            setLoading(true);
            const response = await APIClient.getAuditLog(0, 100);
            setAuditLogs(response.items);
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to load audit log');
        } finally {
            setLoading(false);
        }
    };

    const handleStartScan = async () => {
        try {
            const response = await APIClient.startScan();
            setScanStatus(`Scan started - ${response.pdfs_queued} PDFs queued`);
        } catch (err: any) {
            setScanStatus(`Scan failed: ${err.response?.data?.detail || 'Unknown error'}`);
        }
    };

    const handleResolveDuplicate = async (candidateId: number, keepBookId: number) => {
        try {
            await APIClient.resolveDuplicate(candidateId, keepBookId);
            loadDuplicates();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to resolve duplicate');
        }
    };

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Tabs
                value={tabValue}
                onChange={handleTabChange}
                aria-label="admin tabs"
                sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}
            >
                <Tab label="Duplicates" {...a11yProps(0)} />
                <Tab label="Users" {...a11yProps(1)} />
                <Tab label="Audit Log" {...a11yProps(2)} />
                <Tab label="Library Scan" {...a11yProps(3)} />
            </Tabs>

            {loading && <CircularProgress />}

            <CustomTabPanel value={tabValue} index={0}>
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>ID</TableCell>
                                <TableCell>Book 1</TableCell>
                                <TableCell>Book 2</TableCell>
                                <TableCell>Score</TableCell>
                                <TableCell>Status</TableCell>
                                <TableCell>Actions</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {duplicates.map((dup) => (
                                <TableRow key={dup.id}>
                                    <TableCell>{dup.id}</TableCell>
                                    <TableCell>{dup.book_id_1}</TableCell>
                                    <TableCell>{dup.book_id_2}</TableCell>
                                    <TableCell>{(dup.similarity_score * 100).toFixed(1)}%</TableCell>
                                    <TableCell>{dup.status}</TableCell>
                                    <TableCell>
                                        <Button
                                            size="small"
                                            onClick={() => handleResolveDuplicate(dup.id, dup.book_id_1)}
                                        >
                                            Keep 1
                                        </Button>
                                        <Button
                                            size="small"
                                            onClick={() => handleResolveDuplicate(dup.id, dup.book_id_2)}
                                        >
                                            Keep 2
                                        </Button>
                                    </TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            </CustomTabPanel>

            <CustomTabPanel value={tabValue} index={1}>
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Username</TableCell>
                                <TableCell>Email</TableCell>
                                <TableCell>Role</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {users.map((user) => (
                                <TableRow key={user.id}>
                                    <TableCell>{user.username}</TableCell>
                                    <TableCell>{user.email}</TableCell>
                                    <TableCell>{user.role}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            </CustomTabPanel>

            <CustomTabPanel value={tabValue} index={2}>
                <TableContainer component={Paper}>
                    <Table>
                        <TableHead>
                            <TableRow>
                                <TableCell>Action</TableCell>
                                <TableCell>User</TableCell>
                                <TableCell>Date</TableCell>
                            </TableRow>
                        </TableHead>
                        <TableBody>
                            {auditLogs.map((log) => (
                                <TableRow key={log.id}>
                                    <TableCell>{log.action}</TableCell>
                                    <TableCell>{log.user_id || 'System'}</TableCell>
                                    <TableCell>{new Date(log.created_at).toLocaleString()}</TableCell>
                                </TableRow>
                            ))}
                        </TableBody>
                    </Table>
                </TableContainer>
            </CustomTabPanel>

            <CustomTabPanel value={tabValue} index={3}>
                <Box>
                    <Button variant="contained" onClick={handleStartScan} sx={{ mb: 2 }}>
                        Start Library Scan
                    </Button>
                    {scanStatus && <Alert severity="info">{scanStatus}</Alert>}
                </Box>
            </CustomTabPanel>
        </Container>
    );
};

export default AdminPanel;
