import type { ProjectBrief, ProjectExecutionResponse } from '../types';

function slugify(value: string): string {
  return (
    value
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 48) || 'vertexflow-project'
  );
}

/** Serialises the full orchestration result to a downloadable JSON file. */
export function downloadBlueprintJson(result: ProjectExecutionResponse, brief: ProjectBrief): void {
  const payload = {
    generated_at: new Date().toISOString(),
    brief,
    ...result,
  };

  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `${slugify(brief.project_statement)}-blueprint.json`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

/** Renders the orchestration result as a Markdown document for sharing. */
export function blueprintToMarkdown(
  result: ProjectExecutionResponse,
  brief: ProjectBrief,
): string {
  const blueprint = result.technical_blueprint;
  const lines: string[] = [
    '# VertexFlow Project Blueprint',
    '',
    `**Generated:** ${new Date().toLocaleString()}`,
    '',
    '## Project Brief',
    '',
    brief.project_statement.trim(),
    '',
    `**Target tech stack:** ${brief.target_tech_stack.trim()}`,
    '',
    `**Pipeline status:** ${result.current_status}`,
    '',
    '## Company Vision',
    '',
    result.vision || '_Not generated._',
    '',
    '## Strategic Milestones',
    '',
  ];

  if (result.milestones.length === 0) {
    lines.push('_No milestones generated._', '');
  } else {
    for (const milestone of result.milestones) {
      lines.push(
        `### ${milestone.milestone_id}. ${milestone.title}`,
        '',
        milestone.description,
        '',
        `_Department:_ ${milestone.assigned_department}`,
        '',
      );
    }
  }

  lines.push('## Technical Architecture', '', blueprint.architecture_overview || '_Not generated._', '');

  if (blueprint.database_models && blueprint.database_models.length > 0) {
    lines.push('### Database Models', '');
    for (const model of blueprint.database_models) lines.push(`- ${model}`);
    lines.push('');
  }

  lines.push('## Task Tickets', '');

  const tasks = blueprint.tasks ?? [];
  if (tasks.length === 0) {
    lines.push('_No tickets generated._', '');
  } else {
    for (const task of tasks) {
      lines.push(
        `### ${task.task_id}. ${task.title}`,
        '',
        task.description,
        '',
        `_Difficulty:_ ${task.difficulty}`,
        '',
      );
    }
  }

  return lines.join('\n');
}
