/**
 * T021: Auth store — Firebase-backed reactive auth state.
 *
 * Uses Firebase onAuthStateChanged for reactive state.
 * Session cookie is managed server-side; this store tracks client-side awareness.
 */

import { writable, derived } from 'svelte/store';
import { browser } from '$app/environment';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Role = 'admin' | 'editor' | 'viewer';

export interface AuthUser {
  id: string;
  firebaseUid: string;
  email: string;
  displayName: string;
  role: Role;
  tenantId: string | null;
}

interface AuthState {
  user: AuthUser | null;
  loading: boolean;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

function createAuthStore() {
  const { subscribe, set, update } = writable<AuthState>({
    user: null,
    loading: true,
  });

  let unsubscribeFirebase: (() => void) | null = null;

  function init() {
    if (!browser) return;

    // Lazy import to avoid SSR issues with Firebase client SDK
    import('firebase/auth').then(({ onAuthStateChanged }) => {
      import('$lib/firebase').then(({ auth: firebaseAuth }) => {
        if (!firebaseAuth) return;
        unsubscribeFirebase = onAuthStateChanged(firebaseAuth, (firebaseUser) => {
          if (firebaseUser) {
            // User is signed in on the client.
            // The actual AppUser data comes from the session cookie / server.
            // Here we store minimal client-side awareness.
            update((s) => ({
              ...s,
              user: s.user ?? {
                id: '',
                firebaseUid: firebaseUser.uid,
                email: firebaseUser.email ?? '',
                displayName: firebaseUser.displayName ?? firebaseUser.email ?? '',
                role: 'viewer',
                tenantId: null,
              },
              loading: false,
            }));
          } else {
            set({ user: null, loading: false });
          }
        });
      });
    });
  }

  init();

  return {
    subscribe,

    /** Update local user data (e.g., after session exchange returns server user). */
    setUser(user: AuthUser) {
      set({ user, loading: false });
    },

    clearUser() {
      set({ user: null, loading: false });
    },

    setLoading(loading: boolean) {
      update((s) => ({ ...s, loading }));
    },

    destroy() {
      unsubscribeFirebase?.();
      unsubscribeFirebase = null;
    },
  };
}

export const auth = createAuthStore();

// ---------------------------------------------------------------------------
// Derived helpers
// ---------------------------------------------------------------------------

export const isAuthenticated = derived(auth, ($auth) => $auth.user !== null);

export const currentUser = derived(auth, ($auth) => $auth.user);

export const isAdmin = derived(auth, ($auth) => $auth.user?.role === 'admin');

export const isEditorOrAbove = derived(
  auth,
  ($auth) => $auth.user?.role === 'admin' || $auth.user?.role === 'editor'
);
