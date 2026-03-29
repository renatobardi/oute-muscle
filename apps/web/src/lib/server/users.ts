/**
 * T017: JIT user provisioning (in-memory placeholder).
 *
 * Looks up or creates a local user record keyed by Firebase UID.
 * Real DB integration via FastAPI will replace the in-memory map later.
 */

import { ADMIN_EMAILS } from '$env/static/private';

export type UserRole = 'admin' | 'editor' | 'viewer';

export interface AppUser {
  id: string;
  firebaseUid: string;
  email: string;
  displayName: string;
  role: UserRole;
  tenantId: string | null;
  isActive: boolean;
}

/** In-memory user store — replaced by DB in a future phase. */
const users = new Map<string, AppUser>();

/** Emails that receive admin role on first login. */
function getAdminEmails(): Set<string> {
  const raw = ADMIN_EMAILS ?? '';
  return new Set(
    raw
      .split(',')
      .map((e) => e.trim().toLowerCase())
      .filter(Boolean)
  );
}

/**
 * Find existing user by Firebase UID or create a new one.
 * First-time users get `viewer` role unless their email is in ADMIN_EMAILS.
 */
export function getOrCreateUser(firebaseUid: string, email: string, displayName: string): AppUser {
  const existing = users.get(firebaseUid);
  if (existing) return existing;

  const adminEmails = getAdminEmails();
  const role: UserRole = adminEmails.has(email.toLowerCase()) ? 'admin' : 'viewer';

  const user: AppUser = {
    id: crypto.randomUUID(),
    firebaseUid,
    email,
    displayName,
    role,
    tenantId: null,
    isActive: true,
  };

  users.set(firebaseUid, user);
  return user;
}

/**
 * Retrieve a user by Firebase UID (returns undefined if not found).
 * Exported for hooks.server.ts to populate event.locals.dbUser.
 */
export function getUserByFirebaseUid(firebaseUid: string): AppUser | undefined {
  return users.get(firebaseUid);
}

/** Reset store — useful for tests. */
export function _resetUsers(): void {
  users.clear();
}
