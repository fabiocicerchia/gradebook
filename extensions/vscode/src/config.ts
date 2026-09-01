import * as path from 'node:path';

import * as vscode from 'vscode';

import { Tool } from './types';

export interface Config {
  enable: boolean;
  run: 'onSave' | 'onType' | 'manual';
  debounceMs: number;
  pythonPath: string;
  codePath: string;
  testsPath: string;
  tools: Tool[];
  scanProjectOnStartup: boolean;
  failUnder: number;
  exclude: string[];
  trace: boolean;
}

export function readConfig(scope?: vscode.Uri): Config {
  const c = vscode.workspace.getConfiguration('gradebook', scope);
  return {
    enable: c.get('enable', true),
    run: c.get('run', 'onSave'),
    debounceMs: c.get('debounceMs', 400),
    pythonPath: c.get('pythonPath', 'python3'),
    codePath: c.get('codePath', ''),
    testsPath: c.get('testsPath', ''),
    tools: c.get('tools', ['code', 'tests'] as Tool[]),
    scanProjectOnStartup: c.get('scanProjectOnStartup', true),
    failUnder: c.get('failUnder', 0),
    exclude: c.get('exclude', [] as string[]),
    trace: c.get('trace', false),
  };
}

/** The per-tool module path override, empty meaning "use the installed one". */
export function modulePath(config: Config, tool: Tool): string {
  return tool === 'code' ? config.codePath : config.testsPath;
}

/** Where a checkout keeps each module, relative to the repository root. */
export function checkoutModule(tool: Tool): string {
  return path.join(`gradebook-${tool}`, `gradebook_${tool}.py`);
}

/**
 * Fill an unset module path in from the open workspace.
 *
 * Without this the only fallbacks are an installed package and a path the
 * server derives from its own location — which is right when it runs from a
 * checkout and wrong once the extension is installed from a VSIX, since the
 * server then sits under the extensions directory. Opening the gradebook
 * repository itself is the obvious first thing anyone does, so it has to work
 * before either package is installed.
 */
export function withWorkspaceDefaults(
  config: Config,
  root: string | undefined,
  exists: (file: string) => boolean,
): Config {
  if (!root) {
    return config;
  }
  const resolved = { ...config };
  for (const tool of ['code', 'tests'] as Tool[]) {
    if (modulePath(config, tool)) {
      continue; // an explicit setting always wins
    }
    const candidate = path.join(root, checkoutModule(tool));
    if (exists(candidate)) {
      if (tool === 'code') {
        resolved.codePath = candidate;
      } else {
        resolved.testsPath = candidate;
      }
    }
  }
  return resolved;
}
