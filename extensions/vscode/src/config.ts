import * as vscode from "vscode";

import { Tool } from "./types";

export interface Config {
  /** The open folder, passed to the server as a last-resort module search root. */
  root?: string;
  enable: boolean;
  run: "onSave" | "onType" | "manual";
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
  const c = vscode.workspace.getConfiguration("gradebook", scope);
  return {
    enable: c.get("enable", true),
    run: c.get("run", "onSave"),
    debounceMs: c.get("debounceMs", 400),
    pythonPath: c.get("pythonPath", "python3"),
    codePath: c.get("codePath", ""),
    testsPath: c.get("testsPath", ""),
    tools: c.get("tools", ["code", "tests"] as Tool[]),
    scanProjectOnStartup: c.get("scanProjectOnStartup", true),
    failUnder: c.get("failUnder", 0),
    exclude: c.get("exclude", [] as string[]),
    trace: c.get("trace", false),
  };
}

/** The per-tool module path override, empty meaning "use the installed one". */
export function modulePath(config: Config, tool: Tool): string {
  return tool === "code" ? config.codePath : config.testsPath;
}

/**
 * Hand the open folder to the server as a search root, not as a module path.
 *
 * It used to be probed here and passed as `--code`/`--tests`, which made a
 * workspace copy beat an installed package — a gradebook checkout open in the
 * editor silently graded every other project with its own working tree. The
 * server owns the precedence (explicit setting, installed package, then a
 * checkout), so the workspace goes in at the end of that chain, where it only
 * matters when nothing is installed.
 */
export function withWorkspaceRoot(config: Config, root: string | undefined): Config {
  return { ...config, root };
}
