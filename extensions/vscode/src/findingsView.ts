import * as path from 'node:path';

import * as vscode from 'vscode';

import { Finding, Severity, Tool } from './types';

export type Grouping = 'severity' | 'file' | 'kind';

export const SEVERITIES: Severity[] = ['high', 'medium', 'low'];
export const TOOLS: Tool[] = ['code', 'tests'];

/** What the panel is currently showing. Absent axes mean "everything". */
export interface Filter {
  severities: Set<Severity>;
  tools: Set<Tool>;
}

export const allOf = (): Filter => ({
  severities: new Set(SEVERITIES),
  tools: new Set(TOOLS),
});

/** Whether a filter actually narrows anything, i.e. whether to offer a reset. */
export function isNarrowed(filter: Filter): boolean {
  return filter.severities.size < SEVERITIES.length || filter.tools.size < TOOLS.length;
}

export function matches(entry: Entry, filter: Filter): boolean {
  return filter.severities.has(entry.severity) && filter.tools.has(entry.tool);
}

const SEVERITY_THEME: Record<Severity, { icon: string; colour: string }> = {
  high: { icon: 'flame', colour: 'charts.red' },
  medium: { icon: 'warning', colour: 'charts.yellow' },
  low: { icon: 'info', colour: 'charts.blue' },
};

const SEVERITY_RANK: Record<Severity, number> = { high: 0, medium: 1, low: 2 };

/** A finding plus the tool that found it — the tree shows both together. */
export interface Entry extends Finding {
  tool: Tool;
  /** Absolute path when the finding anchors to a file, otherwise undefined. */
  fsPath?: string;
}

interface Group {
  /** The raw grouping key — unique, unlike the displayed label. */
  key: string;
  label: string;
  description: string;
  icon: vscode.ThemeIcon;
  children: Entry[];
}

type Node = Group | Entry;

const isGroup = (node: Node): node is Group => 'children' in node;

/** Worst first, then by file, then by line — the order the CLI prints. */
export function compareEntries(a: Entry, b: Entry): number {
  return (
    SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity] ||
    (a.file < b.file ? -1 : a.file > b.file ? 1 : 0) ||
    a.line - b.line
  );
}

export function countBySeverity(entries: Entry[]): Record<Severity, number> {
  const counts: Record<Severity, number> = { high: 0, medium: 0, low: 0 };
  for (const entry of entries) {
    counts[entry.severity] += 1;
  }
  return counts;
}

/** The grouping key for one entry, under each of the three modes. */
export function groupKey(entry: Entry, grouping: Grouping): string {
  if (grouping === 'severity') {
    return entry.severity;
  }
  return grouping === 'kind' ? entry.kind : entry.file;
}

/** Group and order entries — pure, so the ordering is testable on its own. */
export function group(entries: Entry[], grouping: Grouping): Array<[string, Entry[]]> {
  const buckets = new Map<string, Entry[]>();
  for (const entry of [...entries].sort(compareEntries)) {
    const key = groupKey(entry, grouping);
    const bucket = buckets.get(key);
    if (bucket) {
      bucket.push(entry);
    } else {
      buckets.set(key, [entry]);
    }
  }
  const keys = [...buckets.keys()];
  if (grouping === 'severity') {
    keys.sort((a, b) => SEVERITY_RANK[a as Severity] - SEVERITY_RANK[b as Severity]);
  } else {
    // Worst-first by the bucket's own worst finding, so the tree opens on what
    // matters rather than on whatever sorts first alphabetically.
    keys.sort(
      (a, b) =>
        compareEntries(buckets.get(a)![0], buckets.get(b)![0]) || (a < b ? -1 : a > b ? 1 : 0),
    );
  }
  return keys.map((key) => [key, buckets.get(key)!]);
}

/** "2 high, 1 low" — the empty buckets are noise, so they are left out. */
export function summarise(counts: Record<Severity, number>): string {
  return (['high', 'medium', 'low'] as Severity[])
    .filter((severity) => counts[severity] > 0)
    .map((severity) => `${counts[severity]} ${severity}`)
    .join(', ');
}

function severityIcon(severity: Severity): vscode.ThemeIcon {
  const theme = SEVERITY_THEME[severity];
  return new vscode.ThemeIcon(theme.icon, new vscode.ThemeColor(theme.colour));
}

/** The Findings panel: every red flag, grouped three ways. */
export class FindingsProvider implements vscode.TreeDataProvider<Node> {
  private readonly emitter = new vscode.EventEmitter<undefined>();
  readonly onDidChangeTreeData = this.emitter.event;

  // Fixed: the panel groups by file and narrows with a filter, which is how
  // the sibling extensions read. A grouping picker and a filter on the same
  // toolbar is two ways to do one thing.
  readonly grouping: Grouping = 'file';
  expanded = true;
  private entries: Entry[] = [];
  private filter: Filter = allOf();
  /**
   * Bumped whenever expand/collapse is asked for.
   *
   * It goes into each group's TreeItem id, and that is the whole trick: VS
   * Code honours `collapsibleState` only the first time it sees an element,
   * and afterwards keeps its own expansion state against that id. Repainting
   * with the same ids is therefore ignored — which is why setting the flag and
   * firing a refresh looks like it does nothing. A new id is a new element, so
   * the state is read afresh.
   */
  private generation = 0;

  setEntries(entries: Entry[]): void {
    this.entries = entries;
    this.refresh();
  }

  /** Everything a scan produced, before the filter. */
  all(): Entry[] {
    return this.entries;
  }

  /** What the panel shows right now. */
  visible(): Entry[] {
    return this.entries.filter((entry) => matches(entry, this.filter));
  }

  currentFilter(): Filter {
    return { severities: new Set(this.filter.severities), tools: new Set(this.filter.tools) };
  }

  get narrowed(): boolean {
    return isNarrowed(this.filter);
  }

  setFilter(filter: Filter): void {
    // An empty pick means "no constraint", not "show nothing" — a toolbar that
    // can hide every finding with one stray click is a trap.
    this.filter = {
      severities: filter.severities.size ? new Set(filter.severities) : new Set(SEVERITIES),
      tools: filter.tools.size ? new Set(filter.tools) : new Set(TOOLS),
    };
    this.refresh();
  }

  clearFilter(): void {
    this.filter = allOf();
    this.refresh();
  }

  /** Expand or collapse every group. */
  setExpanded(expanded: boolean): void {
    this.expanded = expanded;
    this.generation += 1;
    this.refresh();
  }

  /** The id a group renders with — exposed so a test can prove it changes. */
  idFor(key: string): string {
    return `${this.generation}:${this.grouping}:${key}`;
  }

  refresh(): void {
    this.emitter.fire(undefined);
  }

  getChildren(node?: Node): Node[] {
    if (!node) {
      return group(this.visible(), this.grouping).map(([label, children]) => {
        const tally = summarise(countBySeverity(children));
        return {
          key: label,
          label: this.grouping === 'file' ? path.basename(label) : label,
          description:
            this.grouping === 'file' ? `${path.dirname(label)} · ${tally}` : tally,
          icon: severityIcon(children[0].severity),
          children,
        } satisfies Group;
      });
    }
    return isGroup(node) ? node.children : [];
  }

  getTreeItem(node: Node): vscode.TreeItem {
    if (isGroup(node)) {
      const item = new vscode.TreeItem(
        node.label,
        this.expanded
          ? vscode.TreeItemCollapsibleState.Expanded
          : vscode.TreeItemCollapsibleState.Collapsed,
      );
      // Keyed on the group key, not the label: grouping by file shows
      // basenames, and two directories can hold the same one.
      item.id = this.idFor(node.key);
      item.description = node.description;
      item.iconPath = node.icon;
      return item;
    }
    const item = new vscode.TreeItem(node.message, vscode.TreeItemCollapsibleState.None);
    item.description = `${node.kind} · ${node.tool}`;
    item.iconPath = severityIcon(node.severity);
    item.tooltip = `${node.file}${node.line ? `:${node.line}` : ''}\n${node.kind} — ${node.message}`;
    if (node.fsPath) {
      item.resourceUri = vscode.Uri.file(node.fsPath);
      item.command = {
        command: 'vscode.open',
        title: 'Open',
        arguments: [
          vscode.Uri.file(node.fsPath),
          { selection: new vscode.Range(node.line - 1, 0, node.line - 1, 0) },
        ],
      };
    }
    return item;
  }
}
