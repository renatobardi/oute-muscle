/**
 * T140: Auth store — JWT token, user profile, and role helpers.
 * Persists to localStorage on the browser side.
 */

import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';
import { apiClient } from '$lib/api';
import type { Role } from '$lib/api/client';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface AuthUser {
  id: string;
  email: string;
  role: Role;
}

interface AuthState {
  user: AuthUser | null;
  token: string | null;
  loading: boolean;
}

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

function createAuthStore() {
  const storedToken = browser ? localStorage.getItem('auth_token') : null;
  const storedUser = browser ? localStorage.getItem('auth_user') : null;

  const { subscribe, set, update } = writable<AuthState>({
    user: storedUser ? (JSON.parse(storedUser) as AuthUser) : null,
    token: storedToken,
    loading: false,
  });

  return {
    subscribe,

    /** Persist token + user after successful OAuth callback. */
    login(token: string, user: AuthUser) {
      if (browser) {
        localStorage.setItem('auth_token', token);
        localStorage.setItem('auth_user', JSON.stringify(user));
      }
      apiClient.setToken(token);
      set({ user, token, loading: false });
    },

    logout() {
      if (browser) {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
      }
      apiClient.setToken(null);
      set({ user: null, token: null, loading: false });
    },

    setLoading(loading: boolean) {
      update((s) => ({ ...s, loading }));
    },
  };
}

export const auth = createAuthStore();

// ---------------------------------------------------------------------------
// Derived helpers
// ---------------------------------------------------------------------------

export const isAuthenticated = derived(auth, ($auth) => $auth.token !== null && $auth.user !== null);

export const currentUser = derived(auth, ($auth) => $auth.user);

export const isAdmin = derived(auth, ($auth) => $auth.user?.role === 'admin');

export const isEditorOrAbove = derived(
  auth,
  ($auth) => $auth.user?.role === 'admin' || $auth.user?.role === 'editor',
);

/** Returns true if the current user has at least the given role. */
export function hasRole(role: Role): boolean {
  const user = get(currentUser);
  if (!user) return false;
  const hierarchy: Role[] = ['viewer', 'editor', 'admin'];
  return hierarchy.indexOf(user.role) >= hierarchy.indexOf(role);
}
