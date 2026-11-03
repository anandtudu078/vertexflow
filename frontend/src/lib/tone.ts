export type Tone = 'indigo' | 'emerald' | 'amber' | 'rose' | 'slate';

export const TONE_CLASSES: Record<Tone, string> = {
  indigo: 'bg-indigo-500/10 text-indigo-300 border-indigo-500/30',
  emerald: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
  amber: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
  rose: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
  slate: 'bg-slate-500/10 text-slate-300 border-slate-500/30',
};

/** Maps the model's free-form difficulty label onto a badge tone. */
export function difficultyTone(difficulty: string): Tone {
  const value = difficulty.toLowerCase();
  if (value.includes('hard') || value.includes('high') || value.includes('complex')) return 'rose';
  if (value.includes('medium') || value.includes('moderate') || value.includes('mid')) return 'amber';
  if (value.includes('easy') || value.includes('low') || value.includes('simple')) return 'emerald';
  return 'slate';
}
