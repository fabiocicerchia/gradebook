import * as assert from "node:assert/strict";
import { test } from "node:test";
import { modulePath, readConfig, withWorkspaceRoot } from "../config";
import { serverArgv } from "../engine";
import { Store } from "../store";
import { Report } from "../types";
import { configuration } from "./vscode-shim";

test("defaults run both tools on save", () => {
  const config = readConfig();
  assert.deepEqual(config.tools, ["code", "tests"]);
  assert.equal(config.run, "onSave");
  assert.equal(config.debounceMs, 400);
  assert.equal(config.enable, true);
});

test("each tool reads its own module path override", () => {
  configuration.gradebook = { codePath: "/checkout/gradebook-code", testsPath: "" };
  const config = readConfig();
  assert.equal(modulePath(config, "code"), "/checkout/gradebook-code");
  assert.equal(modulePath(config, "tests"), "");
  delete configuration.gradebook;
});

test("the store keeps one report per tool and notifies on change", () => {
  const store = new Store();
  let calls = 0;
  store.onChange(() => (calls += 1));
  const report = { tool: "gradebook-code", score: 1 } as unknown as Report;
  store.set("code", report);
  store.set("tests", report);
  assert.equal(calls, 2);
  assert.equal(store.entries().length, 2);
  store.clear();
  assert.equal(store.get("code"), undefined);
});

// --- module resolution ------------------------------------------------------
//
// The bug these cover: the workspace used to be probed here and passed as
// `--code`/`--tests`, which outranks the installed package on the server side.
// A gradebook checkout open in the editor then graded every other project with
// its own working tree. It goes over as a search root instead, and the server
// only reaches for it when nothing is installed.

test("the open folder travels as a root, not as a module path", () => {
  const resolved = withWorkspaceRoot(readConfig(), "/repo");
  assert.equal(resolved.root, "/repo");
  assert.equal(modulePath(resolved, "code"), "");
  assert.equal(modulePath(resolved, "tests"), "");
});

test("an explicit setting is left untouched", () => {
  configuration.gradebook = { codePath: "/elsewhere/gradebook-code" };
  const resolved = withWorkspaceRoot(readConfig(), "/repo");
  assert.equal(modulePath(resolved, "code"), "/elsewhere/gradebook-code");
  delete configuration.gradebook;
});

test("with no folder open there is no root", () => {
  assert.equal(withWorkspaceRoot(readConfig(), undefined).root, undefined);
});

test("the root reaches the server after the module paths", () => {
  const argv = serverArgv("/ext/server/gradebook_server.py", withWorkspaceRoot(readConfig(), "/repo"));
  assert.deepEqual(argv, ["/ext/server/gradebook_server.py", "--root", "/repo"]);
});
