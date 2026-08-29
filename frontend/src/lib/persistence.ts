/**
 * M28 — LocalStorage persistence for indicator and timeframe state.
 * NO_DEPLOYMENT_SIGNAL. No predictions. No trading signals.
 */

const STORAGE_PREFIX = 'aurora_';
const STORAGE_VERSION = 1;

interface StoredState {
  version: number;
  enabledIndicators: string[];
  indicatorParams: Record<string, Record<string, number>>;
  selectedTimeframe: string;
  selectedAsset: string;
  structureEnabled: boolean;
  contextEnabled: boolean;
}

function safeGetItem(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSetItem(key: string, value: string): boolean {
  try {
    localStorage.setItem(key, value);
    return true;
  } catch {
    return false;
  }
}

function safeRemoveItem(key: string): void {
  try {
    localStorage.removeItem(key);
  } catch { /* ignore */ }
}

export function saveIndicatorState(state: {
  enabledIndicators: Set<string>;
  indicatorParams: Record<string, Record<string, number>>;
  selectedTimeframe: string;
  selectedAsset: string;
  structureEnabled: boolean;
  contextEnabled: boolean;
}): boolean {
  const data: StoredState = {
    version: STORAGE_VERSION,
    enabledIndicators: Array.from(state.enabledIndicators),
    indicatorParams: state.indicatorParams,
    selectedTimeframe: state.selectedTimeframe,
    selectedAsset: state.selectedAsset,
    structureEnabled: state.structureEnabled,
    contextEnabled: state.contextEnabled,
  };
  return safeSetItem(`${STORAGE_PREFIX}indicator_state`, JSON.stringify(data));
}

export function loadIndicatorState(): StoredState | null {
  const raw = safeGetItem(`${STORAGE_PREFIX}indicator_state`);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== 'object') return null;
    if (parsed.version !== STORAGE_VERSION) {
      safeRemoveItem(`${STORAGE_PREFIX}indicator_state`);
      return null;
    }
    if (!Array.isArray(parsed.enabledIndicators)) return null;
    if (typeof parsed.indicatorParams !== 'object') return null;
    return parsed as StoredState;
  } catch {
    safeRemoveItem(`${STORAGE_PREFIX}indicator_state`);
    return null;
  }
}

export function clearIndicatorState(): void {
  safeRemoveItem(`${STORAGE_PREFIX}indicator_state`);
}

export function saveDataMode(mode: 'demo' | 'live'): boolean {
  return safeSetItem(`${STORAGE_PREFIX}data_mode`, mode);
}

export function loadDataMode(): 'demo' | 'live' | null {
  const raw = safeGetItem(`${STORAGE_PREFIX}data_mode`);
  if (raw === 'demo' || raw === 'live') return raw;
  return null;
}
