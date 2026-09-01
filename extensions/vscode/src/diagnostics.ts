import * as fs from 'node:fs';
import * as path from 'node:path';
import * as vscode from 'vscode';
import { Finding, Report, Severity, Tool } from './types';

/** A finding that names a real file at a real line; everything else is workspace-level. */
export function isAnchored(finding: Finding, exists: (file: string) => boolean): boolean {
  // `dependency-cycle` puts "a -> b -> a" in `file` with line 0. Guessing a
  // path for it would squiggle innocent code, so it goes to the report view.
  return finding.line > 0 && exists(finding.file);
}

export function excluded(finding: Finding, prefixes: string[]): boolean {
  return prefixes.some((prefix) => prefix && finding.file.startsWith(prefix));
}

export interface Split {
  anchored: Finding[];
  workspace: Finding[];
}

export function partition(
  findings: Finding[],
  exclude: string[],
  exists: (file: string) => boolean,
): Split {
  const split: Split = { anchored: [], workspace: [] };
  for (const finding of findings) {
    if (excluded(finding, exclude)) {
      continue;
    }
    (isAnchored(finding, exists) ? split.anchored : split.workspace).push(finding);
  }
  return split;
}

const SEVERITIES: Record<Severity, vscode.DiagnosticSeverity> = {
  high: vscode.DiagnosticSeverity.Error,
  medium: vscode.DiagnosticSeverity.Warning,
  low: vscode.DiagnosticSeverity.Information,
};

export function severityOf(finding: Finding): vscode.DiagnosticSeverity {
  return SEVERITIES[finding.severity] ?? vscode.DiagnosticSeverity.Information;
}

/** Group findings by absolute path — one setDiagnostics call per file. */
export function byFile(root: string, findings: Finding[]): Map<string, Finding[]> {
  const grouped = new Map<string, Finding[]>();
  for (const finding of findings) {
    const absolute = path.resolve(root, finding.file);
    const bucket = grouped.get(absolute);
    if (bucket) {
      bucket.push(finding);
    } else {
      grouped.set(absolute, [finding]);
    }
  }
  return grouped;
}

export class Diagnostics {
  private readonly collections = new Map<Tool, vscode.DiagnosticCollection>();

  private collection(tool: Tool): vscode.DiagnosticCollection {
    let collection = this.collections.get(tool);
    if (!collection) {
      collection = vscode.languages.createDiagnosticCollection(`gradebook-${tool}`);
      this.collections.set(tool, collection);
    }
    return collection;
  }

  /** Publishes the anchored findings and hands back the workspace-level ones. */
  publish(tool: Tool, report: Report, exclude: string[]): Finding[] {
    const split = partition(report.findings ?? [], exclude, (file) =>
      fs.existsSync(path.resolve(report.root, file)),
    );
    const collection = this.collection(tool);
    collection.clear();
    for (const [file, findings] of byFile(report.root, split.anchored)) {
      collection.set(
        vscode.Uri.file(file),
        findings.map((finding) => {
          const line = Math.max(0, finding.line - 1);
          const diagnostic = new vscode.Diagnostic(
            new vscode.Range(line, 0, line, Number.MAX_SAFE_INTEGER),
            finding.message,
            severityOf(finding),
          );
          diagnostic.source = `gradebook-${tool}`;
          diagnostic.code = finding.kind;
          return diagnostic;
        }),
      );
    }
    return split.workspace;
  }

  clear(): void {
    for (const collection of this.collections.values()) {
      collection.clear();
    }
  }

  dispose(): void {
    for (const collection of this.collections.values()) {
      collection.dispose();
    }
    this.collections.clear();
  }
}
