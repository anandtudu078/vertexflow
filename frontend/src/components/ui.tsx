import type { HTMLAttributes, ReactNode } from 'react';
import { cn } from '../lib/cn';
import { TONE_CLASSES, type Tone } from '../lib/tone';

export function Badge({
  children,
  tone = 'slate',
  className,
}: {
  children: ReactNode;
  tone?: Tone;
  className?: string;
}) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[11px] font-medium tracking-wide whitespace-nowrap',
        TONE_CLASSES[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}

export function Card({
  children,
  className,
  ...rest
}: { children: ReactNode; className?: string } & HTMLAttributes<HTMLElement>) {
  return (
    <section className={cn('panel p-5 sm:p-6', className)} {...rest}>
      {children}
    </section>
  );
}

export function SectionHeading({
  icon,
  title,
  hint,
  action,
  tone = 'indigo',
}: {
  icon: ReactNode;
  title: string;
  hint?: string;
  action?: ReactNode;
  tone?: Tone;
}) {
  return (
    <div className="mb-4 flex items-start justify-between gap-3">
      <div className="flex items-center gap-3">
        <span
          className={cn(
            'flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border text-base',
            TONE_CLASSES[tone],
          )}
          aria-hidden="true"
        >
          {icon}
        </span>
        <div>
          <h2 className="text-sm font-semibold tracking-wide text-white">{title}</h2>
          {hint ? <p className="mt-0.5 text-xs text-slate-500">{hint}</p> : null}
        </div>
      </div>
      {action}
    </div>
  );
}
