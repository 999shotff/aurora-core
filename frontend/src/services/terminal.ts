/**
 * AURORA Terminal — frontend service.
 * Calls backend terminal aggregation endpoints.
 */

import { API_BASE } from './config';

export interface ProviderStatus {
  category: string;
  name: string;
  detail: string;
  status: 'ready' | 'degraded' | 'unavailable' | 'offline';
  gpu_required: boolean;
}

export interface TerminalStatus {
  status: string;
  uptime_seconds: number;
  providers: ProviderStatus[];
}

export interface TerminalModule {
  status: string;
  [key: string]: unknown;
}

export interface TerminalOverview {
  timestamp: number;
  modules: Record<string, TerminalModule>;
}

export interface CommandResult {
  status: string;
  action?: string;
  target?: string;
  description?: string;
  error?: string;
  hint?: string;
  matches?: Array<{ command: string; target: string; description: string }>;
}

export async function getTerminalStatus(): Promise<TerminalStatus> {
  const res = await fetch(`${API_BASE}/api/v1/terminal/status`);
  if (!res.ok) throw new Error(`Terminal status failed: HTTP ${res.status}`);
  return res.json();
}

export async function getTerminalOverview(): Promise<TerminalOverview> {
  const res = await fetch(`${API_BASE}/api/v1/terminal/overview`);
  if (!res.ok) throw new Error(`Terminal overview failed: HTTP ${res.status}`);
  return res.json();
}

export async function executeTerminalCommand(command: string): Promise<CommandResult> {
  const res = await fetch(`${API_BASE}/api/v1/terminal/command`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ command }),
  });
  if (!res.ok) throw new Error(`Terminal command failed: HTTP ${res.status}`);
  return res.json();
}
