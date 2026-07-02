import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Container,
    Grid,
    TextField,
    Box,
    Button,
    Pagination,
    CircularProgress,
    Alert,
} from '@mui/material';
import BookCard from '../components/Books/BookCard';
import APIClient from '../api/client';

interface Book {
    id: number;
    title: string;
    author: string;
    publisher: string;
}

const LibraryPage: React.FC = () => {
    const navigate = useNavigate();
    const [books, setBooks] = useState<Book[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState('');
    const [page, setPage] = useState(1);
    const [totalPages, setTotalPages] = useState(0);
    const [searchQuery, setSearchQuery] = useState('');
    const [limit] = useState(20);

    useEffect(() => {
        loadBooks();
    }, [page, searchQuery]);

    const loadBooks = async () => {
        setLoading(true);
        setError('');

        try {
            const skip = (page - 1) * limit;

            let response;
            if (searchQuery) {
                response = await APIClient.search(searchQuery, 'title', 100);
            } else {
                response = await APIClient.listBooks(skip, limit);
            }

            setBooks(response.items);
            setTotalPages(Math.ceil(response.total / limit));
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load books');
        } finally {
            setLoading(false);
        }
    };

    const handleSearch = (e: React.ChangeEvent<HTMLInputElement>) => {
        setSearchQuery(e.target.value);
        setPage(1);
    };

    return (
        <Container maxWidth="lg" sx={{ py: 4 }}>
            <Box sx={{ mb: 4 }}>
                <TextField
                    fullWidth
                    placeholder="Search books by title..."
                    value={searchQuery}
                    onChange={handleSearch}
                    variant="outlined"
                />
            </Box>

            {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

            {loading ? (
                <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
                    <CircularProgress />
                </Box>
            ) : (
                <>
                    <Grid container spacing={2} sx={{ mb: 4 }}>
                        {books.map((book) => (
                            <Grid item xs={12} sm={6} md={4} lg={3} key={book.id}>
                                <BookCard
                                    {...book}
                                    onClick={() => navigate(`/books/${book.id}`)}
                                />
                            </Grid>
                        ))}
                    </Grid>

                    {totalPages > 1 && (
                        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                            <Pagination
                                count={totalPages}
                                page={page}
                                onChange={(e, value) => setPage(value)}
                            />
                        </Box>
                    )}
                </>
            )}
        </Container>
    );
};

export default LibraryPage;
