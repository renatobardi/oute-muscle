/**
 * Singleton API client instance.
 * Initialized with the token from the auth store when it becomes available.
 */

import { ApiClient } from './client';
import { browser } from '$app/environment';

export const apiClient = new ApiClient({
  baseUrl: import.meta.env.VITE_API_BASE_URL ?? 'https://api.outemuscle.com/v1',
  token: browser ? localStorage.getItem('auth_token') ?? undefined : undefined,
});

export * from './client';
