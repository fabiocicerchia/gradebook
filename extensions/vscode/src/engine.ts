import { ChildProcess, spawn } from 'node:child_process';
import * as path from 'node:path';

import { Config } from './config';
import { Report, ServerInfo, Tool } from './types';

type Pending = {
  resolve: (value: Record<string, unknown>) => void;
  reject: (error: Error) => void;
};

/** One line of the protocol: a response, or an out-of-band event. */
export interface Message {
  id: number | null;
  ok?: boolean;
  error?: string;
  fatal?: boolean;
  event?: string;
  [key: string]: unknown;
}

/**
 * Split a stream chunk into complete lines plus the leftover. A response can
 * arrive in pieces or several at a time; only whole lines are JSON.
 */
export function frame(buffer: string, chunk: string): { lines: string[]; rest: string } {
  const parts = (buffer + chunk).split('\n');
  const rest = parts.pop() ?? '';
  return { lines: parts.map((line) => line.trim()).filter(Boolean), rest };
}

/** The spawn arguments for a given configuration. */
export function serverArgv(serverPath: string, config: Config): string[] {
  const argv = [serverPath];
  if (config.codePath) {
    argv.push('--code', config.codePath);
  }
  if (config.testsPath) {
    argv.push('--tests', config.testsPath);
  }
  return argv;
}

/**
 * The scan server, one long-lived Python process talking newline-delimited
 * JSON. Restarting it is cheap, so every error path just kills it.
 */
export class Engine {
  private child: ChildProcess | undefined;
  private pending = new Map<number, Pending>();
  private buffer = '';
  private nextId = 1;

  constructor(
    private readonly serverPath: string,
    private config: Config,
    private readonly log: (message: string) => void,
  ) {}

  /** The module paths go on the command line, so a change needs a restart. */
  setConfig(config: Config): void {
    const changed =
      config.pythonPath !== this.config.pythonPath ||
      config.codePath !== this.config.codePath ||
      config.testsPath !== this.config.testsPath;
    this.config = config;
    if (changed) {
      this.restart();
    }
  }

  private start(): ChildProcess {
    if (this.child && !this.child.killed) {
      return this.child;
    }
    const argv = serverArgv(this.serverPath, this.config);
    const child = spawn(this.config.pythonPath, argv, {
      cwd: path.dirname(this.serverPath),
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    child.stdout?.setEncoding('utf8');
    child.stdout?.on('data', (chunk: string) => this.consume(chunk));
    child.stderr?.setEncoding('utf8');
    child.stderr?.on('data', (chunk: string) => this.log(`server: ${chunk.trimEnd()}`));
    child.on('exit', (code) => {
      this.log(`server exited (${code})`);
      this.failAll(new Error(`gradebook server exited (${code})`));
      this.child = undefined;
    });
    child.on('error', (error) => {
      this.failAll(error);
      this.child = undefined;
    });
    this.child = child;
    return child;
  }

  private consume(chunk: string): void {
    const { lines, rest } = frame(this.buffer, chunk);
    this.buffer = rest;
    for (const line of lines) {
      this.dispatch(line);
    }
  }

  private dispatch(line: string): void {
    let message: Message;
    try {
      message = JSON.parse(line) as Message;
    } catch {
      this.log(`unparseable server line: ${line.slice(0, 200)}`);
      return;
    }
    if (this.config.trace) {
      this.log(`<- ${line.slice(0, 400)}`);
    }
    // id 0 is the server talking about itself: ready, or a startup failure it
    // cannot answer any request from.
    if (message.id === 0) {
      if (message.fatal) {
        this.log(`server failed to start: ${message.error}`);
        this.failAll(new Error(message.error ?? 'server failed to start'));
      }
      return;
    }
    const waiter = message.id === null ? undefined : this.pending.get(message.id);
    if (!waiter) {
      return;
    }
    this.pending.delete(message.id as number);
    if (message.ok) {
      waiter.resolve(message);
    } else {
      waiter.reject(new Error(message.error ?? 'unknown server error'));
    }
  }

  private failAll(error: Error): void {
    for (const waiter of this.pending.values()) {
      waiter.reject(error);
    }
    this.pending.clear();
  }

  private send(request: Record<string, unknown>): Promise<Record<string, unknown>> {
    const child = this.start();
    const id = this.nextId++;
    const line = JSON.stringify({ ...request, id });
    if (this.config.trace) {
      this.log(`-> ${line.slice(0, 400)}`);
    }
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      child.stdin?.write(line + '\n', (error) => {
        if (error) {
          this.pending.delete(id);
          reject(error);
        }
      });
    });
  }

  async ping(): Promise<ServerInfo> {
    return (await this.send({ op: 'ping' })) as unknown as ServerInfo;
  }

  async scanProject(root: string, tool: Tool): Promise<Report> {
    const response = await this.send({ op: 'scanProject', root, tool });
    return response.report as Report;
  }

  invalidate(): Promise<Record<string, unknown>> {
    return this.send({ op: 'invalidate' });
  }

  /** Drops answers we no longer want; a running scan is ~0.25s and finishes. */
  cancelAll(): void {
    for (const id of this.pending.keys()) {
      void this.send({ op: 'cancel', cancel: id }).catch(() => undefined);
    }
    this.failAll(new Error('cancelled'));
  }

  restart(): void {
    this.dispose();
    this.start();
  }

  dispose(): void {
    this.failAll(new Error('server stopped'));
    this.child?.kill();
    this.child = undefined;
    this.buffer = '';
  }
}
