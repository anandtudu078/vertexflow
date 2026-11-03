import type { ProductManagerBlueprint } from '../types';
import { CheckIcon, ClipboardIcon } from './Icons';
import { Badge, Card, SectionHeading } from './ui';

export function ProductRequirementsPanel({
  requirements,
}: {
  requirements: Partial<ProductManagerBlueprint>;
}) {
  const userStories = requirements.user_stories ?? [];

  return (
    <Card>
      <SectionHeading
        icon={<ClipboardIcon />}
        title="PM product requirements"
        hint="User stories produced by the PM agent"
        action={
          userStories.length > 0 ? (
            <Badge tone="indigo">
              {userStories.length} {userStories.length === 1 ? 'story' : 'stories'}
            </Badge>
          ) : undefined
        }
      />

      {requirements.product_scope_summary ? (
        <div className="mb-4 rounded-xl border border-slate-800/80 bg-ink-950/60 p-4">
          <h3 className="mb-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
            Product scope
          </h3>
          <p className="text-sm leading-relaxed whitespace-pre-line text-slate-300">
            {requirements.product_scope_summary}
          </p>
        </div>
      ) : null}

      <div>
        <h3 className="mb-2 flex items-center gap-2 text-[11px] font-semibold tracking-wider text-slate-400 uppercase">
          <ClipboardIcon className="h-3.5 w-3.5" />
          User stories
        </h3>
        {userStories.length > 0 ? (
          <ul className="space-y-3">
            {userStories.map((story, index) => (
              <li
                key={`${story.story_id}-${index}`}
                className="rounded-xl border border-slate-800/80 bg-ink-950/60 p-3.5 transition hover:border-indigo-500/25"
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <span className="font-mono text-[10px] tracking-wide text-slate-500">
                    US-{story.story_id}
                  </span>
                  {story.user_role ? (
                    <Badge tone="slate">{story.user_role}</Badge>
                  ) : null}
                </div>
                <p className="mt-1.5 text-sm font-medium text-white">{story.feature_goal}</p>
                {story.acceptance_criteria.length > 0 ? (
                  <ul className="mt-2.5 space-y-1">
                    {story.acceptance_criteria.map((criterion, ci) => (
                      <li key={ci} className="flex items-start gap-2 text-xs leading-relaxed text-slate-400">
                        <CheckIcon className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-400" />
                        {criterion}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </li>
            ))}
          </ul>
        ) : (
          <p className="rounded-xl border border-dashed border-slate-800 bg-ink-950/40 p-4 text-sm text-slate-500 italic">
            The PM agent did not return any user stories.
          </p>
        )}
      </div>
    </Card>
  );
}
