export type Tool = 'code' | 'tests';
export type Severity = 'high' | 'medium' | 'low';

export interface Finding {
  file: string;
  line: number;
  kind: string;
  message: string;
  severity: Severity;
}

export interface Dimension {
  id: string;
  title: string;
  weight: number;
  score: number | null;
  points: number;
  lost: number;
  detail: string;
  advice: string;
}

export interface Recommendation {
  dimension: string;
  points: number;
  advice: string;
}

export interface Report {
  tool: string;
  version: string;
  root: string;
  score: number;
  grade: string;
  dimensions: Dimension[];
  not_scored: string[];
  recommendations: Recommendation[];
  findings: Finding[];
}

export interface ServerInfo {
  protocol: number;
  python: string;
  versions: Record<Tool, string>;
  modules: Record<Tool, string | null>;
  /** Every kind either tool knows, bucketed. Read, never restated here. */
  severityOrder: Record<string, Severity>;
}
