/**
 * T008: Firebase Admin SDK singleton (server-side only).
 *
 * - Cloud Run: Uses Application Default Credentials (ADC)
 * - Local dev: Uses cert from FIREBASE_* env vars
 */
import { initializeApp, getApps, cert, applicationDefault, type App } from 'firebase-admin/app';
import { getAuth, type Auth } from 'firebase-admin/auth';
import { env } from '$env/dynamic/private';

let adminApp: App;

function getAdminApp(): App {
  const existing = getApps();
  if (existing.length > 0) return existing[0];

  const projectId = env.FIREBASE_PROJECT_ID ?? 'oute-488706';
  const clientEmail = env.FIREBASE_CLIENT_EMAIL ?? '';
  const privateKey = env.FIREBASE_PRIVATE_KEY ?? '';

  // Local dev: use certificate if env vars are set
  if (clientEmail && privateKey) {
    adminApp = initializeApp({
      credential: cert({
        projectId,
        clientEmail,
        privateKey: privateKey.replace(/\\n/g, '\n'),
      }),
    });
  } else {
    // Cloud Run: Application Default Credentials
    adminApp = initializeApp({
      credential: applicationDefault(),
      projectId,
    });
  }

  return adminApp;
}

export function getAdminAuth(): Auth {
  return getAuth(getAdminApp());
}
