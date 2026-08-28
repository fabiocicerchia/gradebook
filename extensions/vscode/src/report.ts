import * as vscode from 'vscode';
import { Finding, Report, Tool } from './types';

export interface Section {
  tool: Tool;
  report: Report;
  workspace: Finding[];
}

/** The CLI's bar, so the view and `gradebook-code .` read the same. */
export function bar(score: number | null, width = 20): string {
  if (score === null) {
    return '·'.repeat(width);
  }
  const filled = Math.round(score * width);
  return '█'.repeat(filled) + '░'.repeat(width - filled);
}

/** Exported so a test can build the expected markup with it rather than a
 * second copy of these rules — `Naming & intent` is a real dimension title. */
export function escape(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function sectionHtml(section: Section): string {
  const { report } = section;
  const rows = report.dimensions
    .map(
      (dim) => `<tr>
        <td>${escape(dim.title)}</td>
        <td class="bar">${bar(dim.score)}</td>
        <td class="num">${dim.score === null ? 'n/a' : dim.points.toFixed(1)}/${dim.weight.toFixed(0)}</td>
        <td>${escape(dim.detail)}</td>
      </tr>`,
    )
    .join('\n');
  const wins = (report.recommendations ?? [])
    .map((rec) => `<li><b>+${rec.points.toFixed(1)}</b> ${escape(rec.advice)}</li>`)
    .join('\n');
  const notScored = report.not_scored?.length
    ? `<p class="muted">Not scored (weights redistributed): ${escape(report.not_scored.join(', '))}.</p>`
    : '';
  // Findings with no file to squiggle — a dependency cycle names a loop of
  // modules, not a line — live here rather than on a guessed path.
  const workspace = section.workspace.length
    ? `<h3>Workspace findings (${section.workspace.length})</h3><ul>${section.workspace
        .map((f) => `<li><code>${escape(f.file)}</code> <b>${escape(f.kind)}</b> — ${escape(f.message)}</li>`)
        .join('\n')}</ul>`
    : '';
  return `<section>
    <h2>${escape(report.tool)} — <b>${report.score.toFixed(1)}/100</b> (grade ${escape(report.grade)})</h2>
    <table>${rows}</table>
    ${notScored}
    ${wins ? `<h3>Biggest wins</h3><ul>${wins}</ul>` : ''}
    ${workspace}
  </section>`;
}

export function renderHtml(sections: Section[]): string {
  const body = sections.length
    ? sections.map(sectionHtml).join('\n')
    : '<p class="muted">No scan yet — run <b>gradebook: Scan Workspace</b>.</p>';
  return `<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  body { font-family: var(--vscode-font-family); padding: 1rem; }
  table { border-collapse: collapse; width: 100%; }
  td { padding: 2px 8px; vertical-align: top; }
  .bar { font-family: monospace; white-space: pre; }
  .num { font-family: monospace; text-align: right; white-space: nowrap; }
  .muted { opacity: 0.7; }
  section { margin-bottom: 2rem; }
</style></head>
<body>${body}</body></html>`;
}

export class ReportView {
  private panel: vscode.WebviewPanel | undefined;
  private sections: Section[] = [];

  update(sections: Section[]): void {
    this.sections = sections;
    if (this.panel) {
      this.panel.webview.html = renderHtml(sections);
    }
  }

  show(): void {
    if (!this.panel) {
      this.panel = vscode.window.createWebviewPanel(
        'gradebook.report',
        'gradebook',
        vscode.ViewColumn.Beside,
        { enableScripts: false },
      );
      this.panel.onDidDispose(() => {
        this.panel = undefined;
      });
    }
    this.panel.webview.html = renderHtml(this.sections);
    this.panel.reveal(vscode.ViewColumn.Beside, true);
  }

  dispose(): void {
    this.panel?.dispose();
    this.panel = undefined;
  }
}
