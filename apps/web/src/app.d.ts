/// <reference types="@sveltejs/kit" />

import type { AuthUser } from '$lib/server/auth';
import type { AppUser } from '$lib/server/users';

declare global {
  namespace App {
    interface Locals {
      user?: AuthUser;
      dbUser?: AppUser;
    }
  }
}

export {};
