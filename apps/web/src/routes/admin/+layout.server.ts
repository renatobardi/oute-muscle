/**
 * T046: Admin server guard — only admin role can access /admin routes.
 */
import type { LayoutServerLoad } from './$types';
import { redirect } from '@sveltejs/kit';

export const load: LayoutServerLoad = async ({ locals }) => {
  if (!locals.dbUser || locals.dbUser.role !== 'admin') {
    throw redirect(303, '/');
  }

  return {
    user: locals.user ?? null,
    dbUser: locals.dbUser,
  };
};
