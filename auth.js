/**
 * Simple authentication system for Fed News Monitor
 * Uses localStorage for client-side authentication
 * In production, this should be replaced with proper backend authentication
 */

const AUTH_STORAGE_KEY = 'fednews_auth';
const API_BASE_URL = '/api'; // Will use Vercel serverless functions

class AuthManager {
    constructor() {
        this.user = this.loadUser();
    }

    loadUser() {
        try {
            const stored = localStorage.getItem(AUTH_STORAGE_KEY);
            if (stored) {
                const user = JSON.parse(stored);
                // Check if token is expired
                if (user.expiresAt && new Date(user.expiresAt) < new Date()) {
                    this.logout();
                    return null;
                }
                return user;
            }
        } catch (e) {
            console.error('Error loading user:', e);
        }
        return null;
    }

    saveUser(user) {
        try {
            localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(user));
            this.user = user;
        } catch (e) {
            console.error('Error saving user:', e);
        }
    }

    async register(email, password, name) {
        try {
            // In production, this would call a real API
            // For now, we'll use a simple client-side approach
            const response = await fetch(`${API_BASE_URL}/register`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password, name })
            });

            if (response.ok) {
                const data = await response.json();
                const user = {
                    email: data.email,
                    name: data.name,
                    role: 'member',
                    token: data.token,
                    expiresAt: data.expiresAt
                };
                this.saveUser(user);
                return { success: true, user };
            } else {
                const error = await response.json();
                return { success: false, error: error.message || 'Registration failed' };
            }
        } catch (e) {
            // Fallback: simple client-side registration (for demo)
            console.warn('API not available, using client-side auth:', e);
            const user = {
                email,
                name,
                role: 'member',
                token: this.generateToken(email),
                expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString() // 30 days
            };
            this.saveUser(user);
            return { success: true, user };
        }
    }

    async login(email, password) {
        try {
            const response = await fetch(`${API_BASE_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (response.ok) {
                const data = await response.json();
                const user = {
                    email: data.email,
                    name: data.name,
                    role: data.role || 'member',
                    token: data.token,
                    expiresAt: data.expiresAt
                };
                this.saveUser(user);
                return { success: true, user };
            } else {
                const error = await response.json();
                return { success: false, error: error.message || 'Login failed' };
            }
        } catch (e) {
            // Fallback: simple client-side login (for demo)
            console.warn('API not available, using client-side auth:', e);
            // Check if user exists in localStorage (demo only)
            const existingUsers = JSON.parse(localStorage.getItem('fednews_users') || '{}');
            if (existingUsers[email] && existingUsers[email].password === password) {
                const user = {
                    email,
                    name: existingUsers[email].name,
                    role: 'member',
                    token: this.generateToken(email),
                    expiresAt: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString()
                };
                this.saveUser(user);
                return { success: true, user };
            }
            return { success: false, error: 'Invalid credentials' };
        }
    }

    logout() {
        localStorage.removeItem(AUTH_STORAGE_KEY);
        this.user = null;
    }

    isAuthenticated() {
        return this.user !== null;
    }

    isMember() {
        return this.user && this.user.role === 'member';
    }

    getUser() {
        return this.user;
    }

    generateToken(email) {
        // Simple token generation (in production, use proper JWT)
        return btoa(email + ':' + Date.now()).replace(/[^a-zA-Z0-9]/g, '');
    }
}

// Global auth manager instance
const authManager = new AuthManager();
