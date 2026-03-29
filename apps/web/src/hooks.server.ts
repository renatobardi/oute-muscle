/**
 * T010: SvelteKit server hooks — authenticate + gateUser sequence.
 *
 * Every request passes through:
 * 1. authenticate: Verify __session cookie or Bearer token
 * 2. gateUser: Check user state (pending approval, deactivated)
 */
import type { Handle } from '@sveltejs/kit';
import { sequence } from '@sveltejs/kit/hooks';
import { redirect } from '@sveltejs/kit';
import { verifyAuthToken } from '$lib/server/auth';
import { getUserByFirebaseUid } from '$lib/server/users';

const PUBLIC_PATHS = ['/auth/login', '/auth/register', '/pending', '/api/auth/session'];

const authenticate: Handle = async ({ event, resolve }) => {
  const path = event.url.pathname;

  // Skip auth for public paths
  if (PUBLIC_PATHS.some((p) => path.startsWith(p))) {
    return resolve(event);
  }

  const user = await verifyAuthToken(event);
  if (!user) {
    if (path.startsWith('/api/')) {
      return new Response(JSON.stringify({ error: 'Unauthorized' }), {
        status: 401,
        headers: { 'Content-Type': 'application/json' },
      });
    }
    throw redirect(302, '/auth/login');
  }

  event.locals.user = user;

  // Populate dbUser from in-memory user store for gateUser hook
  const dbUser = getUserByFirebaseUid(user.uid);
  if (dbUser) {
    event.locals.dbUser = dbUser;
  }

  return resolve(event);
};

const gateUser: Handle = async ({ event, resolve }) => {
  const path = event.url.pathname;
  if (PUBLIC_PATHS.some((p) => path.startsWith(p))) {
    return resolve(event);
  }

  const dbUser = event.locals.dbUser;

  // Redirect deactivated users
  if (dbUser && !dbUser.isActive) {
    throw redirect(302, '/auth/login?reason=deactivated');
  }

  // Redirect tenant-less users to pending page (except admin)
  if (dbUser && !dbUser.tenantId && dbUser.role !== 'admin' && !path.startsWith('/pending')) {
    throw redirect(302, '/pending');
  }

  return resolve(event);
};

export const handle = sequence(authenticate, gateUser);
