/**
 * T009: Server-side auth verification.
 *
 * Supports two auth methods:
 * 1. __session cookie (primary — SSR navigation)
 * 2. Bearer token (API calls from client JS)
 */
import type { RequestEvent } from '@sveltejs/kit';
import type { DecodedIdToken } from 'firebase-admin/auth';
import { getAdminAuth } from './firebase-admin';

export interface AuthUser {
  uid: string;
  email: string;
  displayName?: string;
  emailVerified: boolean;
}

export async function verifyAuthToken(event: RequestEvent): Promise<AuthUser | null> {
  // 1. Try Bearer token (API calls)
  const authorization = event.request.headers.get('authorization');
  if (authorization?.startsWith('Bearer ')) {
    const token = authorization.slice(7);
    try {
      const decoded = await getAdminAuth().verifyIdToken(token);
      return mapDecodedToken(decoded);
    } catch {
      return null;
    }
  }

  // 2. Try __session cookie (SSR navigation)
  const sessionCookie = event.cookies.get('__session');
  if (sessionCookie) {
    try {
      const decoded = await getAdminAuth().verifySessionCookie(sessionCookie, true);
      return mapDecodedToken(decoded);
    } catch {
      return null;
    }
  }

  return null;
}

function mapDecodedToken(decoded: DecodedIdToken): AuthUser {
  return {
    uid: decoded.uid,
    email: decoded.email ?? '',
    displayName: decoded.name ?? decoded.email ?? '',
    emailVerified: decoded.email_verified ?? false,
  };
}
