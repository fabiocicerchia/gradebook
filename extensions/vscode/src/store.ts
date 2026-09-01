import { Report, Tool } from './types';

/**
 * The latest report per tool, plus whoever wants to hear about a new one.
 * Small enough that a Map and a listener list beat an event framework.
 */
export class Store {
  private reports = new Map<Tool, Report>();
  private listeners: Array<() => void> = [];

  set(tool: Tool, report: Report): void {
    this.reports.set(tool, report);
    for (const listener of this.listeners) {
      listener();
    }
  }

  get(tool: Tool): Report | undefined {
    return this.reports.get(tool);
  }

  entries(): Array<[Tool, Report]> {
    return [...this.reports.entries()];
  }

  clear(): void {
    this.reports.clear();
  }

  onChange(listener: () => void): void {
    this.listeners.push(listener);
  }
}
