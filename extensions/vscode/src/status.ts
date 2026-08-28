import * as vscode from 'vscode';

import { Report, Tool } from './types';

/** What the status bar says. Pure, so the wording is testable. */
export interface Entry {
  text: string;
  tooltip: string;
  /** Either score is below `failUnder` — worth colouring, not worth a popup. */
  warn: boolean;
}

const ICON: Record<Tool, string> = { code: 'code', tests: 'beaker' };

/** One tool's piece of the label: an icon, its grade and its score. */
export function fragmentFor(tool: Tool, report: Report): string {
  return `$(${ICON[tool]}) ${report.grade} ${report.score.toFixed(1)}`;
}

function detail(report: Report): string[] {
  const lines = [`${report.tool} ${report.version} — ${report.score.toFixed(1)}/100, grade ${report.grade}`];
  if (report.not_scored?.length) {
    lines.push(`  not scored: ${report.not_scored.join(', ')}`);
  }
  const top = report.recommendations?.[0];
  if (top) {
    lines.push(`  biggest win: +${top.points.toFixed(1)} ${top.advice}`);
  }
  return lines;
}

/**
 * Both scores in one entry, so they sit next to each other.
 *
 * One item rather than two: the status bar orders items by priority and
 * competes with every other extension for space, so two separate entries can
 * end up apart or with something else wedged between them. Together they read
 * as one measurement of one repository, which is what they are.
 */
export function summaryFor(reports: Array<[Tool, Report]>, failUnder: number): Entry | undefined {
  if (reports.length === 0) {
    return undefined;
  }
  // Fixed order, never the order the scans happened to finish in: a status bar
  // that reshuffles itself between saves cannot be read at a glance.
  const ordered = (['code', 'tests'] as Tool[])
    .map((tool) => reports.find(([candidate]) => candidate === tool))
    .filter((entry): entry is [Tool, Report] => entry !== undefined);
  return {
    text: ordered.map(([tool, report]) => fragmentFor(tool, report)).join('  '),
    tooltip: ['gradebook', ...ordered.flatMap(([, report]) => detail(report)), '', 'Click to open the report.'].join('\n'),
    warn: failUnder > 0 && ordered.some(([, report]) => report.score < failUnder),
  };
}

export class StatusBar {
  private item: vscode.StatusBarItem | undefined;

  update(reports: Array<[Tool, Report]>, failUnder: number): void {
    const entry = summaryFor(reports, failUnder);
    if (!entry) {
      this.hide();
      return;
    }
    if (!this.item) {
      this.item = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
      this.item.command = 'gradebook.showReport';
    }
    this.item.text = entry.text;
    this.item.tooltip = entry.tooltip;
    this.item.backgroundColor = entry.warn
      ? new vscode.ThemeColor('statusBarItem.warningBackground')
      : undefined;
    this.item.show();
  }

  hide(): void {
    this.item?.hide();
  }

  dispose(): void {
    this.item?.dispose();
    this.item = undefined;
  }
}
