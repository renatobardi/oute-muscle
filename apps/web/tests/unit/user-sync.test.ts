/**
 * T014: Unit tests for JIT user provisioning (getOrCreateUser).
 *
 * Verifies: first login creates user with viewer role,
 * admin email gets admin role, subsequent calls return existing user.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

vi.mock('$env/static/private', () => ({
  ADMIN_EMAILS: 'admin@oute.pro,boss@company.com',
  FIREBASE_PROJECT_ID: 'oute-test',
  FIREBASE_CLIENT_EMAIL: '',
  FIREBASE_PRIVATE_KEY: '',
}));

import { getOrCreateUser, getUserByFirebaseUid, _resetUsers } from '../../src/lib/server/users';

describe('getOrCreateUser', () => {
  beforeEach(() => {
    _resetUsers();
  });

  it('creates a new user with viewer role on first login', () => {
    const user = getOrCreateUser('uid-1', 'dev@example.com', 'Dev User');

    expect(user.firebaseUid).toBe('uid-1');
    expect(user.email).toBe('dev@example.com');
    expect(user.displayName).toBe('Dev User');
    expect(user.role).toBe('viewer');
    expect(user.tenantId).toBeNull();
    expect(user.isActive).toBe(true);
    expect(user.id).toBeTruthy();
  });

  it('returns existing user on subsequent calls', () => {
    const first = getOrCreateUser('uid-2', 'dev@example.com', 'Dev User');
    const second = getOrCreateUser('uid-2', 'dev@example.com', 'Dev User');

    expect(second.id).toBe(first.id);
  });

  it('assigns admin role when email is in ADMIN_EMAILS', () => {
    const user = getOrCreateUser('uid-admin', 'admin@oute.pro', 'Admin');

    expect(user.role).toBe('admin');
  });

  it('admin email matching is case-insensitive', () => {
    const user = getOrCreateUser('uid-admin2', 'ADMIN@OUTE.PRO', 'Admin Upper');

    expect(user.role).toBe('admin');
  });

  it('supports multiple admin emails', () => {
    const user = getOrCreateUser('uid-boss', 'boss@company.com', 'Boss');

    expect(user.role).toBe('admin');
  });

  it('can be retrieved by firebase UID after creation', () => {
    getOrCreateUser('uid-3', 'test@example.com', 'Tester');
    const found = getUserByFirebaseUid('uid-3');

    expect(found).toBeDefined();
    expect(found!.email).toBe('test@example.com');
  });

  it('returns undefined for unknown firebase UID', () => {
    const found = getUserByFirebaseUid('unknown-uid');

    expect(found).toBeUndefined();
  });
});
