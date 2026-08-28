import * as fs from 'node:fs';
import * as path from 'node:path';

import * as vscode from 'vscode';

import { Config, readConfig, withWorkspaceDefaults } from './config';
import { Diagnostics } from './diagnostics';
import { Engine } from './engine';
import { Entry, FindingsProvider, Filter, SEVERITIES, TOOLS } from './findingsView';
import { ReportView, Section } from './report';
import { StatusBar } from './status';
import { Store } from './store';
import { Tool } from './types';

let engine: Engine | undefined;
let timer: NodeJS.Timeout | undefined;

export function activate(context: vscode.ExtensionContext): void {
  const output = vscode.window.createOutputChannel('gradebook');
  const log = (message: string) => output.appendLine(message);
  const diagnostics = new Diagnostics();
  const view = new ReportView();
  const store = new Store();
  const findings = new FindingsProvider();
  const status = new StatusBar();

  const workspaceRoot = () => vscode.workspace.workspaceFolders?.[0]?.uri.fsPath;
  const currentConfig = (): Config =>
    withWorkspaceDefaults(readConfig(), workspaceRoot(), fs.existsSync);

  let config: Config = currentConfig();
  const serverPath = context.asAbsolutePath(path.join('server', 'gradebook_server.py'));
  engine = new Engine(serverPath, config, log);

  const sections = (): Section[] =>
    store.entries().map(([tool, report]) => ({
      tool,
      report,
      workspace: diagnostics.publish(tool, report, config.exclude),
    }));

  const refresh = () => {
    const current = sections();
    view.update(current);

    // Every finding the tree shows, anchored or not — the flags are the
    // product, so none of them may be dropped on the way to the panel.
    const entries: Entry[] = [];
    for (const section of current) {
      const skip = new Set(section.workspace);
      for (const finding of section.report.findings ?? []) {
        if (config.exclude.some((prefix) => prefix && finding.file.startsWith(prefix))) {
          continue;
        }
        const fsPath = path.resolve(section.report.root, finding.file);
        entries.push({
          ...finding,
          tool: section.tool,
          fsPath: skip.has(finding) ? undefined : fsPath,
        });
      }
    }
    findings.setEntries(entries);
    // Two keys, not one: the panel has to tell "never scanned" from "scanned
    // and clean", or a tidy workspace looks exactly like a broken extension.
    void vscode.commands.executeCommand('setContext', 'gradebook.scanned', current.length > 0);
    void vscode.commands.executeCommand('setContext', 'gradebook.hasFindings', entries.length > 0);

    status.update(store.entries(), config.failUnder);
  };

  // Shown once per distinct message: a scan runs on every save, and the same
  // "not installed" popup ten times is worse than not showing it at all.
  const reported = new Set<string>();
  const report = (message: string) => {
    log(message);
    if (reported.has(message)) {
      return;
    }
    reported.add(message);
    void vscode.window
      .showErrorMessage(`gradebook: ${message}`, 'Open Settings', 'Show Log')
      .then((choice) => {
        if (choice === 'Show Log') {
          output.show();
        } else if (choice === 'Open Settings') {
          void vscode.commands.executeCommand('workbench.action.openSettings', 'gradebook');
        }
      });
  };

  async function scan(): Promise<void> {
    const folder = vscode.workspace.workspaceFolders?.[0];
    if (!config.enable || !folder || !engine) {
      return;
    }
    // Whole-repo, not per-file: hotspots need `git log` and duplication is
    // cross-file, so there is no meaningful single-file score.
    for (const tool of config.tools as Tool[]) {
      try {
        store.set(tool, await engine.scanProject(folder.uri.fsPath, tool));
        reported.clear(); // a working scan retires the old complaint
      } catch (error) {
        report((error as Error).message);
      }
    }
    refresh();
  }

  const schedule = (delay: number) => {
    if (timer) {
      clearTimeout(timer);
    }
    timer = setTimeout(() => void scan(), delay);
  };

  const refreshFilterState = () => {
    void vscode.commands.executeCommand('setContext', 'gradebook.filtered', findings.narrowed);
  };

  async function pickFilters(): Promise<void> {
    const all = findings.all();
    const count = (predicate: (entry: Entry) => boolean) => `${all.filter(predicate).length}`;
    const current = findings.currentFilter();

    type Item = vscode.QuickPickItem & { severity?: Entry['severity']; tool?: Entry['tool'] };
    const items: Item[] = [
      { label: 'Severity', kind: vscode.QuickPickItemKind.Separator },
      ...SEVERITIES.map((severity) => ({
        label: severity,
        description: count((entry) => entry.severity === severity),
        picked: current.severities.has(severity),
        severity,
      })),
      { label: 'Tool', kind: vscode.QuickPickItemKind.Separator },
      ...TOOLS.map((tool) => ({
        label: `gradebook-${tool}`,
        description: count((entry) => entry.tool === tool),
        picked: current.tools.has(tool),
        tool,
      })),
    ];

    const chosen = await vscode.window.showQuickPick(items, {
      canPickMany: true,
      title: 'gradebook: show which findings',
    });
    if (!chosen) {
      return; // dismissed, so nothing changes
    }
    const filter: Filter = {
      severities: new Set(chosen.map((item) => item.severity).filter(Boolean) as Entry['severity'][]),
      tools: new Set(chosen.map((item) => item.tool).filter(Boolean) as Entry['tool'][]),
    };
    findings.setFilter(filter);
    refreshFilterState();
  }

  context.subscriptions.push(
    output,
    { dispose: () => status.dispose() },
    // showCollapseAll gives the view VS Code's own collapse button, which is
    // implemented inside the tree and always works.
    vscode.window.createTreeView('gradebook.findings', {
      treeDataProvider: findings,
      showCollapseAll: true,
    }),
    { dispose: () => diagnostics.dispose() },
    { dispose: () => view.dispose() },
    { dispose: () => engine?.dispose() },
    vscode.commands.registerCommand('gradebook.scanWorkspace', () => scan()),
    vscode.commands.registerCommand('gradebook.showReport', () => {
      view.update(sections());
      view.show();
    }),
    vscode.commands.registerCommand('gradebook.showOutput', () => output.show()),
    vscode.commands.registerCommand('gradebook.restartServer', () => {
      engine?.restart();
      return scan();
    }),
    vscode.commands.registerCommand('gradebook.cancelScan', () => engine?.cancelAll()),
    vscode.commands.registerCommand('gradebook.filterFindings', () => pickFilters()),
    vscode.commands.registerCommand('gradebook.clearFilter', () => {
      findings.clearFilter();
      refreshFilterState();
    }),
    vscode.commands.registerCommand('gradebook.expandAll', () => findings.setExpanded(true)),
    vscode.workspace.onDidChangeConfiguration((event) => {
      if (!event.affectsConfiguration('gradebook')) {
        return;
      }
      config = currentConfig();
      engine?.setConfig(config);
      if (!config.enable) {
        diagnostics.clear();
        store.clear();
        findings.setEntries([]);
        status.hide();
      }
    }),
    vscode.workspace.onDidSaveTextDocument(() => {
      if (config.run === 'onSave' || config.run === 'onType') {
        schedule(0);
      }
    }),
    vscode.workspace.onDidChangeTextDocument(() => {
      if (config.run === 'onType') {
        schedule(config.debounceMs);
      }
    }),
  );

  refreshFilterState();
  if (config.scanProjectOnStartup) {
    void scan();
  }
}

export function deactivate(): void {
  if (timer) {
    clearTimeout(timer);
  }
  engine?.dispose();
  engine = undefined;
}
