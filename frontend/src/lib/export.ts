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

  const pm = result.product_requirements;
  if (pm) {
    lines.push('## Product Requirements', '');

    if (pm.product_scope_summary) {
      lines.push('### Product Scope', '', pm.product_scope_summary, '');
    }

    const stories = pm.user_stories ?? [];
    if (stories.length > 0) {
      lines.push('### User Stories', '');
      for (const story of stories) {
        lines.push(
          `#### US-${story.story_id}: ${story.feature_goal}`,
          '',
          `_Role:_ ${story.user_role}`,
          '',
        );
        if (story.acceptance_criteria.length > 0) {
          lines.push('**Acceptance criteria:**', '');
          for (const criterion of story.acceptance_criteria) {
            lines.push(`- ${criterion}`);
          }
          lines.push('');
        }
      }
    }
  }

  const be = result.backend_code;
  if (be?.module_name || be?.database_models_code || be?.api_endpoints_code) {
    lines.push('## Backend Code', '');
    if (be.module_name) lines.push(`**Module:** \`${be.module_name}\``, '');

    if (be.database_models_code) {
      lines.push('### Database Models', '', '```python', be.database_models_code, '```', '');
    }
    if (be.api_endpoints_code) {
      lines.push('### API Endpoints', '', '```python', be.api_endpoints_code, '```', '');
    }
    if (be.dependencies_required && be.dependencies_required.length > 0) {
      lines.push('### Dependencies', '');
      for (const dep of be.dependencies_required) lines.push(`- \`${dep}\``);
      lines.push('');
    }
  }

  const fe = result.frontend_code;
  if (fe?.component_name || fe?.react_tsx_code) {
    lines.push('## Frontend Code', '');
    if (fe.component_name) lines.push(`**Component:** \`${fe.component_name}\``, '');
    if (fe.state_management_summary) lines.push(fe.state_management_summary, '');

    if (fe.react_tsx_code) {
      lines.push('```tsx', fe.react_tsx_code, '```', '');
    }
    if (fe.tailwind_styles_used && fe.tailwind_styles_used.length > 0) {
      lines.push('### Tailwind Classes', '');
      for (const cls of fe.tailwind_styles_used) lines.push(`- \`${cls}\``);
      lines.push('');
    }
  }

  const audit = result.security_audit;
  if (audit?.overall_status || (audit?.vulnerabilities && audit.vulnerabilities.length > 0)) {
    lines.push('## Security Audit', '');
    if (audit.security_score !== undefined) {
      lines.push(`**Score:** ${audit.security_score} / 100`);
    }
    if (audit.overall_status) lines.push(`**Status:** ${audit.overall_status}`, '');
    if (audit.compliance_notes) lines.push(audit.compliance_notes, '');

    const vulns = audit.vulnerabilities ?? [];
    if (vulns.length > 0) {
      lines.push('### Vulnerabilities', '');
      for (const vuln of vulns) {
        lines.push(
          `#### ${vuln.vulnerability_id} (${vuln.severity})`,
          '',
          vuln.description,
          '',
          `_Remediation:_ ${vuln.remediation}`,
          '',
        );
      }
    }
  }

  return lines.join('\n');
}
