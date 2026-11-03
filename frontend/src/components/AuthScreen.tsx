import { useState, type FormEvent } from 'react';
import { ApiError } from '../lib/api';
import { loginAccount, registerAccount } from '../lib/auth';
import { cn } from '../lib/cn';
import type { AuthUser } from '../types';
import { AlertIcon, RefreshIcon } from './Icons';

type Mode = 'login' | 'register';

const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const MIN_PASSWORD_LENGTH = 8;

export function AuthScreen({
  onAuthenticated,
  backendOnline,
}: {
  onAuthenticated: (user: AuthUser) => void;
  backendOnline: boolean;
}) {
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [confirm, setConfirm] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState<boolean>(false);

  const emailValid = EMAIL_PATTERN.test(email.trim());
  const passwordValid = password.length >= MIN_PASSWORD_LENGTH;
  const passwordsMatch = mode === 'login' || password === confirm;
  const canSubmit = emailValid && passwordValid && passwordsMatch && !pending;

  const switchMode = (next: Mode) => {
    setMode(next);
    setError(null);
    setConfirm('');
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!canSubmit) return;

    setPending(true);
    setError(null);

    try {
      const credentials = { email: email.trim(), password };
      const user =
        mode === 'register'
          ? await registerAccount(credentials)
          : await loginAccount(credentials);
      onAuthenticated(user);
    } catch (caught) {
      setError(
        caught instanceof ApiError
          ? caught.message
          : 'Something went wrong. Please try again.',
      );
    } finally {
      setPending(false);
    }
  };

  return (
    <div className="flex min-h-[calc(100vh-8rem)] items-center justify-center px-4 py-10">
      <div className="w-full max-w-md animate-rise">
        <div className="mb-6 text-center">
          <span className="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl border border-indigo-500/30 bg-indigo-500/10">
            <svg viewBox="0 0 32 32" className="h-6 w-6" fill="none" aria-hidden="true">
              <path
                d="M8 9l8 14 8-14"
                stroke="#818cf8"
                strokeWidth="2.8"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <circle cx="16" cy="7.5" r="2.2" fill="#34d399" />
            </svg>
          </span>
          <h1 className="text-xl font-semibold tracking-tight text-white">
            Vertex<span className="text-indigo-400">Flow</span>
          </h1>
          <p className="mt-1 text-sm text-slate-400">
            {mode === 'login'
              ? 'Sign in to launch the agent swarm.'
              : 'Create an account to launch the agent swarm.'}
          </p>
        </div>

        <div className="panel p-6">
          <div className="mb-5 grid grid-cols-2 gap-1 rounded-xl border border-slate-800 bg-ink-950/70 p-1">
            {(['login', 'register'] as const).map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => switchMode(option)}
                className={cn(
                  'cursor-pointer rounded-lg px-3 py-1.5 text-xs font-medium transition',
                  mode === option
                    ? 'bg-indigo-600 text-white shadow-sm shadow-indigo-600/30'
                    : 'text-slate-400 hover:text-slate-200',
                )}
              >
                {option === 'login' ? 'Sign in' : 'Create account'}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="space-y-4" noValidate>
            <div>
              <label
                htmlFor="auth-email"
                className="mb-2 block text-[11px] font-semibold tracking-wider text-slate-400 uppercase"
              >
                Email
              </label>
              <input
                id="auth-email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@company.com"
                className="field"
              />
            </div>

            <div>
              <label
                htmlFor="auth-password"
                className="mb-2 block text-[11px] font-semibold tracking-wider text-slate-400 uppercase"
              >
                Password
              </label>
              <input
                id="auth-password"
                type="password"
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                required
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder={`At least ${MIN_PASSWORD_LENGTH} characters`}
                className="field"
              />
              {mode === 'register' && password.length > 0 && !passwordValid ? (
                <p className="mt-2 text-[11px] text-amber-400">
                  Use at least {MIN_PASSWORD_LENGTH} characters.
                </p>
              ) : null}
            </div>

            {mode === 'register' ? (
              <div>
                <label
                  htmlFor="auth-confirm"
                  className="mb-2 block text-[11px] font-semibold tracking-wider text-slate-400 uppercase"
                >
                  Confirm password
                </label>
                <input
                  id="auth-confirm"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={confirm}
                  onChange={(event) => setConfirm(event.target.value)}
                  placeholder="Repeat your password"
                  className="field"
                />
                {confirm.length > 0 && !passwordsMatch ? (
                  <p className="mt-2 text-[11px] text-amber-400">Passwords do not match.</p>
                ) : null}
              </div>
            ) : null}

            {error ? (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-xl border border-rose-500/30 bg-rose-500/10 p-3"
              >
                <AlertIcon className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" />
                <p className="text-xs leading-relaxed text-rose-200">{error}</p>
              </div>
            ) : null}

            <button
              type="submit"
              disabled={!canSubmit}
              className={cn(
                'inline-flex w-full items-center justify-center gap-2 rounded-xl px-4 py-3 text-sm font-semibold text-white transition',
                canSubmit
                  ? 'cursor-pointer bg-indigo-600 shadow-lg shadow-indigo-600/25 hover:bg-indigo-500 active:scale-[0.99]'
                  : 'cursor-not-allowed bg-indigo-600/40 text-indigo-100/60',
              )}
            >
              {pending ? (
                <>
                  <RefreshIcon className="h-4 w-4 animate-spin" />
                  {mode === 'login' ? 'Signing in…' : 'Creating account…'}
                </>
              ) : mode === 'login' ? (
                'Sign in'
              ) : (
                'Create account'
              )}
            </button>
          </form>

          <p className="mt-4 border-t border-slate-800/80 pt-4 text-center text-[11px] leading-relaxed text-slate-500">
            {backendOnline
              ? 'Sessions last 7 days and are stored in an HttpOnly cookie.'
              : 'The backend is unreachable — sign-in will fail until it is running.'}
          </p>
        </div>
      </div>
    </div>
  );
}
