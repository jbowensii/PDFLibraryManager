import React, { useState, useEffect } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import {
    Container,
    Paper,
    Typography,
    Button,
    Box,
    CircularProgress,
    Alert,
    Grid,
    Dialog,
    TextField,
} from '@mui/material';
import BookCard from '../components/Books/BookCard';
import APIClient from '../api/client';

interface Collection {
    id: number;
    name: string;
    description?: string;
    books?: Book[];
}

interface Book {
    id: number;
    title: string;
    author: string;
    publisher: string;
}

const CollectionsPage: React.FC = () => {
    const { collectionId } = useParams<{ collectionId: string }>();
    const navigate = useNavigate();
    const [collections, setCollections] = useState<Collection[]>([]);
    const [selectedCollection, setSelectedCollection] = useState<Collection | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [openDialog, setOpenDialog] = useState(false);
    const [newCollectionName, setNewCollectionName] = useState('');
    const [newCollectionDesc, setNewCollectionDesc] = useState('');

    useEffect(() => {
        loadCollections();
    }, []);

    const loadCollections = async () => {
        try {
            setLoading(true);
            const response = await APIClient.listCollections();
            setCollections(response.items);

            if (collectionId) {
                const collection = await APIClient.getCollection(parseInt(collectionId));
                setSelectedCollection(collection);
            }
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load collections');
        } finally {
            setLoading(false);
        }
    };

    const handleCreateCollection = async () => {
        try {
            await APIClient.createCollection(newCollectionName, newCollectionDesc);
            setOpenDialog(false);
            setNewCollectionName('');
            setNewCollectionDesc('');
            loadCollections();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to create collection');
        }
    };

    const handleRemoveBook = async (bookId: number) => {
        if (!selectedCollection) return;

        try {
            await APIClient.removeBookFromCollection(selectedCollection.id, bookId);
            loadCollections();
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to remove book');
        }
    };

    if (loading) {
        return (
            <Container sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
            </Container>
        );
    }

    if (selectedCollection) {
        return (
            <Container maxWidth="lg" sx={{ py: 4 }}>
                <Button onClick={() => setSelectedCollection(null)} sx={{ mb: 2 }}>
                    &lt; Back to Collections
                </Button>

                <Paper sx={{ p: 3, mb: 4 }}>
                    <Typography variant="h4" gutterBottom>
                        {selectedCollection.name}
                    </Typography>
                    {selectedCollection.description && (
                        <Typography variant="body1" color="text.secondary">
                            {selectedCollection.description}
                        </Typography>
                    )}
                </Paper>

                <Grid container spacing={2}>
                    {selectedCollection.books?.map((book) => (
                        <Grid item xs={12} sm={6} md={4} lg={3} key={book.id}>
                            <BookCard
                                {...book}
                                onClick={() => navigate(`/books/${book.id}`)}
                            />
                        </Grid>
                    ))}
                </Grid>
            </Container>
        );
    }

    return (
        <Container maxWidth="md" sx={{ py: 4 }}>
            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            <Box sx={{ mb: 4 }}>
                <Button variant="contained" onClick={() => setOpenDialog(true)}>
                    Create Collection
                </Button>
            </Box>

            <Grid container spacing={2}>
                {collections.map((col) => (
                    <Grid item xs={12} sm={6} key={col.id}>
                        <Paper
                            sx={{
                                p: 2,
                                cursor: 'pointer',
                                '&:hover': { boxShadow: 3 },
                            }}
                            onClick={() => setSelectedCollection(col)}
                        >
                            <Typography variant="h6">{col.name}</Typography>
                            {col.description && (
                                <Typography variant="body2" color="text.secondary">
                                    {col.description}
                                </Typography>
                            )}
                            <Typography variant="caption" color="text.secondary">
                                {col.books?.length || 0} books
                            </Typography>
                        </Paper>
                    </Grid>
                ))}
            </Grid>

            <Dialog open={openDialog} onClose={() => setOpenDialog(false)} maxWidth="sm" fullWidth>
                <Box sx={{ p: 3 }}>
                    <Typography variant="h6" gutterBottom>
                        Create New Collection
                    </Typography>
                    <TextField
                        fullWidth
                        label="Name"
                        value={newCollectionName}
                        onChange={(e) => setNewCollectionName(e.target.value)}
                        margin="normal"
                    />
                    <TextField
                        fullWidth
                        label="Description"
                        value={newCollectionDesc}
                        onChange={(e) => setNewCollectionDesc(e.target.value)}
                        margin="normal"
                        multiline
                        rows={3}
                    />
                    <Box sx={{ mt: 2, display: 'flex', gap: 1 }}>
                        <Button variant="contained" onClick={handleCreateCollection}>
                            Create
                        </Button>
                        <Button onClick={() => setOpenDialog(false)}>Cancel</Button>
                    </Box>
                </Box>
            </Dialog>
        </Container>
    );
};

export default CollectionsPage;
