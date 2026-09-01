// Enough of the `vscode` module to exercise the parts of the extension that do
// not need an editor.
//
// The alternative is running tests inside a downloaded VS Code, which is slow,
// networked, and tests the editor rather than this code. The modules worth
// covering — finding routing, the store, the report, the tree — touch almost
// none of the API, so a stub of what they touch buys real coverage for a page
// of code.

class EventEmitter<T> {
  private listeners: Array<(value: T) => void> = [];
  readonly event = (listener: (value: T) => void) => {
    this.listeners.push(listener);
    return { dispose: () => undefined };
  };
  fire(value: T): void {
    for (const listener of [...this.listeners]) {
      listener(value);
    }
  }
  dispose(): void {
    this.listeners = [];
  }
}

class ThemeIcon {
  static readonly File = new ThemeIcon('file');
  constructor(
    readonly id: string,
    readonly color?: unknown,
  ) {}
}

class TreeItem {
  description?: string;
  iconPath?: unknown;
  resourceUri?: unknown;
  tooltip?: unknown;
  command?: unknown;
  contextValue?: string;
  constructor(
    readonly label: string,
    readonly collapsibleState?: number,
  ) {}
}

class DiagnosticCollection {
  readonly entries = new Map<string, unknown[]>();
  constructor(readonly name: string) {}
  set(uri: { fsPath: string }, diagnostics: unknown[]): void {
    this.entries.set(uri.fsPath, diagnostics);
  }
  clear(): void {
    this.entries.clear();
  }
  dispose(): void {
    this.entries.clear();
  }
}

/** Set by a test to decide what `getConfiguration(section).get(key)` returns. */
export const configuration: Record<string, Record<string, unknown>> = {};

/** Every collection handed out, so a test can look at what was published. */
export const collections: DiagnosticCollection[] = [];

/** Command handlers registered by activate(), so a test can invoke them. */
export const commands = new Map<string, (...args: unknown[]) => unknown>();

/** Whatever the extension tried to tell the user. */
export const messages: string[] = [];

/** setContext keys the extension set, so a test can assert on the panel state. */
export const contexts = new Map<string, unknown>();

/** Tree providers handed to createTreeView, so a test can walk the real tree. */
export const trees = new Map<string, { getChildren(node?: unknown): unknown[] }>();

export const vscode = {
  EventEmitter,
  ThemeIcon,
  ThemeColor: class {
    constructor(readonly id: string) {}
  },
  TreeItem,
  TreeItemCollapsibleState: { None: 0, Collapsed: 1, Expanded: 2 },
  DiagnosticSeverity: { Error: 0, Warning: 1, Information: 2, Hint: 3 },
  StatusBarAlignment: { Left: 1, Right: 2 },
  ViewColumn: { Active: -1, Beside: -2 },
  Range: class {
    constructor(
      readonly startLine: number,
      readonly startCharacter: number,
      readonly endLine: number,
      readonly endCharacter: number,
    ) {}
  },
  Diagnostic: class {
    source?: string;
    code?: string;
    constructor(
      readonly range: unknown,
      readonly message: string,
      readonly severity: number,
    ) {}
  },
  Uri: { file: (fsPath: string) => ({ fsPath, scheme: 'file' }) },
  languages: {
    createDiagnosticCollection(name: string): DiagnosticCollection {
      const collection = new DiagnosticCollection(name);
      collections.push(collection);
      return collection;
    },
  },
  workspace: {
    workspaceFolders: undefined as Array<{ uri: { fsPath: string } }> | undefined,
    getConfiguration: (section: string) => ({
      get: <T>(key: string, fallback: T): T => {
        const values = configuration[section] ?? {};
        return key in values ? (values[key] as T) : fallback;
      },
    }),
    onDidSaveTextDocument: () => ({ dispose() {} }),
    onDidChangeTextDocument: () => ({ dispose() {} }),
    onDidChangeConfiguration: () => ({ dispose() {} }),
  },
  window: {
    createOutputChannel: () => ({ appendLine() {}, show() {}, dispose() {} }),
    createStatusBarItem: () => ({ text: '', command: '', show() {}, hide() {}, dispose() {} }),
    createTreeView: (
      id: string,
      options: { treeDataProvider: { getChildren(node?: unknown): unknown[] } },
    ) => {
      trees.set(id, options.treeDataProvider);
      return { dispose: () => trees.delete(id) };
    },
    showQuickPick: () => Promise.resolve(undefined),
    showErrorMessage: (message: string) => {
      messages.push(message);
      return Promise.resolve(undefined);
    },
    createWebviewPanel: () => ({
      webview: { html: '' },
      reveal() {},
      onDidDispose() {},
      dispose() {},
    }),
  },
  commands: {
    registerCommand: (id: string, handler: (...args: unknown[]) => unknown) => {
      commands.set(id, handler);
      return { dispose: () => commands.delete(id) };
    },
    executeCommand: (command: string, key?: string, value?: unknown) => {
      if (command === 'setContext' && key !== undefined) {
        contexts.set(key, value);
      }
      return Promise.resolve();
    },
  },
};
