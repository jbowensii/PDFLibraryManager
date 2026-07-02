import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
    Container,
    Paper,
    Typography,
    Button,
    Box,
    CircularProgress,
    Alert,
    Select,
    MenuItem,
} from '@mui/material';
import APIClient from '../api/client';

interface Book {
    id: number;
    title: string;
    author: string;
    publisher: string;
    isbn?: string;
    file_size_bytes?: number;
    created_at?: string;
}

interface Collection {
    id: number;
    name: string;
}

const BookDetailPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const [book, setBook] = useState<Book | null>(null);
    const [collections, setCollections] = useState<Collection[]>([]);
    const [selectedCollection, setSelectedCollection] = useState('');
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');

    useEffect(() => {
        loadBook();
        loadCollections();
    }, [id]);

    const loadBook = async () => {
        try {
            if (!id) return;
            const data = await APIClient.getBook(parseInt(id));
            setBook(data);
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load book');
        } finally {
            setLoading(false);
        }
    };

    const loadCollections = async () => {
        try {
            const response = await APIClient.listCollections();
            setCollections(response.items);
        } catch (err: any) {
            console.error('Failed to load collections');
        }
    };

    const handleAddToCollection = async () => {
        if (!selectedCollection || !book) return;

        try {
            await APIClient.addBookToCollection(parseInt(selectedCollection), book.id);
            alert('Book added to collection');
            setSelectedCollection('');
        } catch (err: any) {
            alert(err.response?.data?.detail || 'Failed to add book to collection');
        }
    };

    if (loading) {
        return (
            <Container sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                <CircularProgress />
            </Container>
        );
    }

    if (error) {
        return (
            <Container maxWidth="md" sx={{ py: 4 }}>
                <Alert severity="error">{error}</Alert>
                <Button onClick={() => navigate('/library')} sx={{ mt: 2 }}>
                    Back to Library
                </Button>
            </Container>
        );
    }

    if (!book) {
        return <Typography>Book not found</Typography>;
    }

    return (
        <Container maxWidth="md" sx={{ py: 4 }}>
            <Paper sx={{ p: 4 }}>
                <Typography variant="h4" gutterBottom>
                    {book.title}
                </Typography>
                <Typography variant="h6" color="text.secondary" gutterBottom>
                    by {book.author}
                </Typography>
                <Typography variant="body1" gutterBottom>
                    <strong>Publisher:</strong> {book.publisher}
                </Typography>
                {book.isbn && (
                    <Typography variant="body1" gutterBottom>
                        <strong>ISBN:</strong> {book.isbn}
                    </Typography>
                )}
                {book.file_size_bytes && (
                    <Typography variant="body1" gutterBottom>
                        <strong>File Size:</strong> {(book.file_size_bytes / 1024 / 1024).toFixed(2)} MB
                    </Typography>
                )}

                <Box sx={{ mt: 4 }}>
                    <Typography variant="h6" gutterBottom>
                        Add to Collection
                    </Typography>
                    <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
                        <Select
                            value={selectedCollection}
                            onChange={(e) => setSelectedCollection(e.target.value)}
                            sx={{ minWidth: 200 }}
                        >
                            <MenuItem value="">-- Select Collection --</MenuItem>
                            {collections.map((col) => (
                                <MenuItem key={col.id} value={col.id}>
                                    {col.name}
                                </MenuItem>
                            ))}
                        </Select>
                        <Button
                            variant="contained"
                            onClick={handleAddToCollection}
                            disabled={!selectedCollection}
                        >
                            Add
                        </Button>
                    </Box>
                </Box>

                <Box sx={{ mt: 4 }}>
                    <Button variant="outlined" onClick={() => navigate('/library')}>
                        Back to Library
                    </Button>
                </Box>
            </Paper>
        </Container>
    );
};

export default BookDetailPage;
