/**
 * T015 + T016: Session exchange endpoint.
 *
 * POST — Exchange Firebase ID token for a server-side session cookie.
 * DELETE — Clear the session cookie (logout).
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { getAdminAuth } from '$lib/server/firebase-admin';
import { getOrCreateUser } from '$lib/server/users';

const SESSION_COOKIE_NAME = '__session';
const SESSION_MAX_AGE = 60 * 60 * 24 * 5; // 5 days in seconds
const SESSION_MAX_AGE_MS = SESSION_MAX_AGE * 1000;

export const POST: RequestHandler = async ({ request, cookies }) => {
  const body = await request.json().catch(() => null);
  const idToken: string | undefined = body?.idToken;

  if (!idToken) {
    return json({ error: 'Missing idToken' }, { status: 400 });
  }

  try {
    const adminAuth = getAdminAuth();
    const decoded = await adminAuth.verifyIdToken(idToken);

    const sessionCookie = await adminAuth.createSessionCookie(idToken, {
      expiresIn: SESSION_MAX_AGE_MS,
    });

    cookies.set(SESSION_COOKIE_NAME, sessionCookie, {
      maxAge: SESSION_MAX_AGE,
      httpOnly: true,
      secure: true,
      sameSite: 'lax',
      path: '/',
    });

    const user = getOrCreateUser(
      decoded.uid,
      decoded.email ?? '',
      decoded.name ?? decoded.email ?? ''
    );

    return json({ user });
  } catch {
    return json({ error: 'Invalid or expired token' }, { status: 401 });
  }
};

export const DELETE: RequestHandler = async ({ cookies }) => {
  cookies.delete(SESSION_COOKIE_NAME, { path: '/' });
  return json({ status: 'logged_out' });
};
