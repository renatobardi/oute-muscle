/**
 * T007: Firebase client SDK singleton.
 *
 * Shared Firebase project oute-488706 (same user pool as oute.me).
 * Client-side only — guarded by `browser` check for SSR safety.
 */
import { initializeApp, getApps, type FirebaseApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, type Auth } from 'firebase/auth';
import { browser } from '$app/environment';
import { env } from '$env/dynamic/public';

const firebaseConfig = {
  apiKey: env.PUBLIC_FIREBASE_API_KEY ?? '',
  authDomain: env.PUBLIC_FIREBASE_AUTH_DOMAIN ?? 'oute-488706.firebaseapp.com',
  projectId: env.PUBLIC_FIREBASE_PROJECT_ID ?? 'oute-488706',
  appId: env.PUBLIC_FIREBASE_APP_ID ?? '',
};

function getFirebaseClient(): FirebaseApp {
  const existing = getApps();
  if (existing.length > 0) return existing[0];
  return initializeApp(firebaseConfig);
}

// Only initialize on client-side (SSR-safe)
export const app: FirebaseApp | null = browser ? getFirebaseClient() : null;
export const auth: Auth | null = browser && app ? getAuth(app) : null;
export const googleProvider = new GoogleAuthProvider();
