import React from 'react';
import { Card, CardContent, CardMedia, Typography, Box } from '@mui/material';

interface BookCardProps {
    id: number;
    title: string;
    author: string;
    publisher: string;
    onClick?: () => void;
}

const BookCard: React.FC<BookCardProps> = ({ id, title, author, publisher, onClick }) => {
    return (
        <Card
            onClick={onClick}
            sx={{
                cursor: 'pointer',
                height: '100%',
                display: 'flex',
                flexDirection: 'column',
                transition: 'transform 0.2s',
                '&:hover': {
                    transform: 'translateY(-4px)',
                    boxShadow: 4,
                },
            }}
        >
            <CardMedia
                sx={{
                    height: 200,
                    backgroundColor: '#e0e0e0',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: '#999',
                }}
            >
                <Typography>No Cover</Typography>
            </CardMedia>
            <CardContent>
                <Typography gutterBottom variant="h6" component="div" noWrap>
                    {title}
                </Typography>
                <Typography variant="body2" color="text.secondary" noWrap>
                    {author}
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                    {publisher}
                </Typography>
            </CardContent>
        </Card>
    );
};

export default BookCard;
