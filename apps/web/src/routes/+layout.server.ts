/**
 * T011: Root layout server load — pass auth user to all pages.
 */
import type { LayoutServerLoad } from './$types';

export const load: LayoutServerLoad = async ({ locals }) => {
  return {
    user: locals.user ?? null,
    dbUser: locals.dbUser ?? null
  };
};
