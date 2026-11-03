import type { AuthUser, Credentials } from '../types';
import { API_BASE, ApiError, readErrorDetail } from './api';

const AUTH_TIMEOUT_MS = 15_000;

async function authFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), AUTH_TIMEOUT_MS);

  try {
    return await fetch(`${API_BASE}${path}`, {
      credentials: 'same-origin',
      headers: { Accept: 'application/json', ...(init.headers ?? {}) },
      signal: controller.signal,
      ...init,
    });
  } catch (error) {
    const name = error instanceof Error ? error.name : '';
    if (name === 'AbortError') {
      throw new ApiError('The authentication request timed out. Try again.');
    }
    throw new ApiError(
      'Could not reach the backend. Make sure the FastAPI server is running on port 8000.',
    );
  } finally {
    window.clearTimeout(timer);
  }
}

async function readUser(response: Response): Promise<AuthUser> {
  if (!response.ok) {
    throw new ApiError(await readErrorDetail(response), response.status);
  }
  return (await response.json()) as AuthUser;
}

export async function registerAccount(credentials: Credentials): Promise<AuthUser> {
  const response = await authFetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });
  return readUser(response);
}

export async function loginAccount(credentials: Credentials): Promise<AuthUser> {
  const response = await authFetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(credentials),
  });
  return readUser(response);
}

export async function logoutAccount(): Promise<void> {
  try {
    await authFetch('/api/auth/logout', { method: 'POST' });
  } catch {
    // The cookie is cleared client-side by the server response either way; a
    // failed logout call should not trap the user in the dashboard.
  }
}

/** Returns the signed-in user, or null when the session is missing/expired. */
export async function fetchCurrentUser(): Promise<AuthUser | null> {
  const response = await authFetch('/api/auth/me');

  if (response.status === 401) return null;
  return readUser(response);
}
