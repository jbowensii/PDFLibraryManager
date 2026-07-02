import axios, { AxiosInstance, AxiosError } from 'axios';

interface LoginResponse {
    access_token: string;
    token_type: string;
}

interface UserResponse {
    id: number;
    username: string;
    email: string;
    role: string;
    created_at: string;
    updated_at: string;
}

interface Book {
    id: number;
    title: string;
    author: string;
    publisher: string;
    isbn?: string;
    content_hash?: string;
    ocr_error_count?: number;
    is_duplicate?: boolean;
    duplicate_parent_id?: number | null;
    created_at?: string;
    updated_at?: string;
}

interface BookDetailResponse extends Book {
    filesystem_path?: string;
    file_size_bytes?: number;
}

interface BooksResponse {
    total: number;
    items: Book[];
}

interface Collection {
    id: number;
    user_id: number;
    name: string;
    description?: string;
    created_at: string;
    updated_at: string;
    books?: Book[];
}

interface CollectionsResponse {
    total: number;
    items: Collection[];
}

interface SearchResponse {
    total: number;
    items: Book[];
}

interface DuplicateCandidate {
    id: number;
    book_id_1: number;
    book_id_2: number;
    similarity_score: number;
    status: string;
    notes?: string;
    created_at: string;
    updated_at: string;
}

interface DuplicatesResponse {
    total: number;
    items: DuplicateCandidate[];
}

interface User {
    id: number;
    username: string;
    email: string;
    role: string;
    created_at: string;
}

interface UsersResponse {
    total: number;
    items: User[];
}

interface AuditLog {
    id: number;
    user_id?: number;
    action: string;
    details?: string;
    created_at: string;
}

interface AuditLogsResponse {
    total: number;
    items: AuditLog[];
}

class APIClient {
    private instance: AxiosInstance;

    constructor() {
        // Relative URL: the Vite dev server (dev) and nginx (production)
        // both proxy /api to the backend, so the same build works on any host.
        const baseURL = '/api/v1';

        this.instance = axios.create({
            baseURL,
            headers: {
                'Content-Type': 'application/json',
            },
        });

        // Request interceptor: add authorization header
        this.instance.interceptors.request.use((config) => {
            const token = localStorage.getItem('access_token');
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }
            return config;
        });

        // Response interceptor: handle 401 errors
        this.instance.interceptors.response.use(
            (response) => response,
            (error: AxiosError) => {
                if (error.response?.status === 401) {
                    localStorage.removeItem('access_token');
                    window.location.href = '/login';
                }
                return Promise.reject(error);
            }
        );
    }

    // Auth endpoints
    async register(username: string, email: string, password: string): Promise<UserResponse> {
        const response = await this.instance.post<UserResponse>('/auth/register', {
            username,
            email,
            password,
        });
        return response.data;
    }

    async login(username: string, password: string): Promise<LoginResponse> {
        const response = await this.instance.post<LoginResponse>('/auth/login', {
            username,
            password,
        });
        return response.data;
    }

    async getCurrentUser(): Promise<UserResponse> {
        const response = await this.instance.get<UserResponse>('/auth/me');
        return response.data;
    }

    // Books endpoints
    async listBooks(skip: number = 0, limit: number = 20): Promise<BooksResponse> {
        const response = await this.instance.get<BooksResponse>('/books/', {
            params: { skip, limit },
        });
        return response.data;
    }

    async getBook(id: number): Promise<BookDetailResponse> {
        const response = await this.instance.get<BookDetailResponse>(`/books/${id}`);
        return response.data;
    }

    async deleteBook(id: number): Promise<void> {
        await this.instance.delete(`/books/${id}`);
    }

    // Collections endpoints
    async createCollection(name: string, description?: string): Promise<Collection> {
        const response = await this.instance.post<Collection>('/collections/', {
            name,
            description,
        });
        return response.data;
    }

    async listCollections(skip: number = 0, limit: number = 50): Promise<CollectionsResponse> {
        const response = await this.instance.get<CollectionsResponse>('/collections/', {
            params: { skip, limit },
        });
        return response.data;
    }

    async getCollection(id: number): Promise<Collection> {
        const response = await this.instance.get<Collection>(`/collections/${id}`);
        return response.data;
    }

    async addBookToCollection(collectionId: number, bookId: number): Promise<void> {
        await this.instance.post(`/collections/${collectionId}/books`, undefined, {
            params: { book_id: bookId },
        });
    }

    async removeBookFromCollection(collectionId: number, bookId: number): Promise<void> {
        await this.instance.delete(`/collections/${collectionId}/books/${bookId}`);
    }

    // Search endpoints
    async search(q: string, searchType: string = 'title', limit: number = 20): Promise<SearchResponse> {
        const response = await this.instance.get<SearchResponse>('/search/', {
            params: { q, search_type: searchType, limit },
        });
        return response.data;
    }

    // Duplicates endpoints
    async listDuplicates(skip: number = 0, limit: number = 20): Promise<DuplicatesResponse> {
        const response = await this.instance.get<DuplicatesResponse>('/duplicates/', {
            params: { skip, limit },
        });
        return response.data;
    }

    async getDuplicate(id: number): Promise<DuplicateCandidate> {
        const response = await this.instance.get<DuplicateCandidate>(`/duplicates/${id}`);
        return response.data;
    }

    async resolveDuplicate(candidateId: number, keepBookId: number): Promise<any> {
        const response = await this.instance.post(`/duplicates/${candidateId}/resolve`, {
            keep_book_id: keepBookId,
        });
        return response.data;
    }

    // Admin endpoints
    async listUsers(skip: number = 0, limit: number = 50): Promise<UsersResponse> {
        const response = await this.instance.get<UsersResponse>('/admin/users', {
            params: { skip, limit },
        });
        return response.data;
    }

    async createUser(username: string, email: string, password: string): Promise<User> {
        const response = await this.instance.post<User>('/admin/users', {
            username,
            email,
            password,
        });
        return response.data;
    }

    async updateUserRole(userId: number, role: string): Promise<User> {
        const response = await this.instance.patch<User>(`/admin/users/${userId}`, {
            role,
        });
        return response.data;
    }

    async deleteUser(userId: number): Promise<void> {
        await this.instance.delete(`/admin/users/${userId}`);
    }

    async getAuditLog(skip: number = 0, limit: number = 100): Promise<AuditLogsResponse> {
        const response = await this.instance.get<AuditLogsResponse>('/admin/audit-log', {
            params: { skip, limit },
        });
        return response.data;
    }

    // Library endpoints
    async startScan(sourceDir?: string): Promise<any> {
        const response = await this.instance.post('/library/scan', {
            source_dir: sourceDir,
        });
        return response.data;
    }

    async getScanStatus(jobId: number): Promise<any> {
        const response = await this.instance.get(`/library/scan/${jobId}`);
        return response.data;
    }
}

export default new APIClient();
