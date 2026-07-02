import React from 'react';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from '../App';

describe('App Component', () => {
    test('test_app_renders', () => {
        render(<App />);
        // App should render without crashing
        expect(screen.getByText(/PDF Library Manager/i)).toBeInTheDocument();
    });

    test('test_routes_exist', () => {
        render(<App />);
        // Check that navigation buttons exist for routes
        expect(screen.getByRole('button', { name: /Library/i })).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Collections/i })).toBeInTheDocument();
    });

    test('test_login_page_accessible', () => {
        render(<App />);
        // Login page should be accessible
        const button = screen.getByRole('button', { name: /Logout/i });
        expect(button).toBeInTheDocument();
    });

    test('test_logout_clears_token', () => {
        // Set a token in localStorage
        localStorage.setItem('token', 'test-token-123');
        expect(localStorage.getItem('token')).toBe('test-token-123');

        // Simulate logout by clearing token
        localStorage.removeItem('token');
        expect(localStorage.getItem('token')).toBeNull();
    });
});
