/**
 * T008: Firebase Admin SDK singleton (server-side only).
 *
 * - Cloud Run: Uses Application Default Credentials (ADC)
 * - Local dev: Uses cert from FIREBASE_* env vars
 */
import {
  initializeApp,
  getApps,
  cert,
  applicationDefault,
  type App
} from 'firebase-admin/app';
import { getAuth, type Auth } from 'firebase-admin/auth';
import { FIREBASE_PROJECT_ID, FIREBASE_CLIENT_EMAIL, FIREBASE_PRIVATE_KEY } from '$env/static/private';

let adminApp: App;

function getAdminApp(): App {
  const existing = getApps();
  if (existing.length > 0) return existing[0];

  // Local dev: use certificate if env vars are set
  if (FIREBASE_CLIENT_EMAIL && FIREBASE_PRIVATE_KEY) {
    adminApp = initializeApp({
      credential: cert({
        projectId: FIREBASE_PROJECT_ID,
        clientEmail: FIREBASE_CLIENT_EMAIL,
        privateKey: FIREBASE_PRIVATE_KEY.replace(/\\n/g, '\n')
      })
    });
  } else {
    // Cloud Run: Application Default Credentials
    adminApp = initializeApp({
      credential: applicationDefault(),
      projectId: FIREBASE_PROJECT_ID
    });
  }

  return adminApp;
}

export function getAdminAuth(): Auth {
  return getAuth(getAdminApp());
}
