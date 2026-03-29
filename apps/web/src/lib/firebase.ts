/**
 * T007: Firebase client SDK singleton.
 *
 * Shared Firebase project oute-488706 (same user pool as oute.me).
 * Client-side only — never import this from server-side code.
 */
import { initializeApp, getApps, type FirebaseApp } from 'firebase/app';
import { getAuth, GoogleAuthProvider, type Auth } from 'firebase/auth';

import {
  PUBLIC_FIREBASE_API_KEY,
  PUBLIC_FIREBASE_AUTH_DOMAIN,
  PUBLIC_FIREBASE_PROJECT_ID,
  PUBLIC_FIREBASE_APP_ID
} from '$env/static/public';

const firebaseConfig = {
  apiKey: PUBLIC_FIREBASE_API_KEY,
  authDomain: PUBLIC_FIREBASE_AUTH_DOMAIN,
  projectId: PUBLIC_FIREBASE_PROJECT_ID,
  appId: PUBLIC_FIREBASE_APP_ID
};

function getFirebaseClient(): FirebaseApp {
  const existing = getApps();
  if (existing.length > 0) return existing[0];
  return initializeApp(firebaseConfig);
}

export const app: FirebaseApp = getFirebaseClient();
export const auth: Auth = getAuth(app);
export const googleProvider = new GoogleAuthProvider();
