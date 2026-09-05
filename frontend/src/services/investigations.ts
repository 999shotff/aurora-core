import type { Investigation, Sourced } from '../types/domain';

/**
 * No investigation/evidence backend exists in this repo yet (the real backend
 * only serves market OHLCV and geo processing). This adapter is the seam a
 * future real API would plug into — the UI consumes `Sourced<T>` either way,
 * so nothing downstream needs to change when a real source is wired in.
 */

const DEMO_INVESTIGATIONS: Investigation[] = [
  {
    id: 'inv_01', title: 'BTC-USD volatility regime shift',
    question: 'Has the volatility regime for BTC-USD structurally shifted since the last halving?',
    status: 'active', domain: 'market', confidence: 'medium', evidenceCount: 14,
    createdAt: '2026-08-14T09:00:00Z', updatedAt: '2026-09-02T11:20:00Z',
  },
  {
    id: 'inv_02', title: 'AOI-7 vegetation change, Q3',
    question: 'Is there measurable vegetation loss in AOI-7 over the last quarter?',
    status: 'active', domain: 'geo', confidence: 'high', evidenceCount: 22,
    createdAt: '2026-07-30T09:00:00Z', updatedAt: '2026-09-01T16:40:00Z',
  },
  {
    id: 'inv_03', title: 'Cross-asset correlation breakdown',
    question: 'Are traditional cross-asset correlations breaking down this cycle?',
    status: 'paused', domain: 'market', confidence: 'low', evidenceCount: 6,
    createdAt: '2026-08-01T09:00:00Z', updatedAt: '2026-08-20T10:00:00Z',
  },
  {
    id: 'inv_04', title: 'AOI-3 land-use classification review',
    question: 'Does the automated land-use classifier disagree with prior manual review in AOI-3?',
    status: 'concluded', domain: 'geo', confidence: 'high', evidenceCount: 31,
    createdAt: '2026-06-10T09:00:00Z', updatedAt: '2026-07-18T14:00:00Z',
  },
];

function delay<T>(value: T, ms = 220): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(value), ms));
}

export async function listInvestigations(): Promise<Sourced<Investigation[]>> {
  const data = await delay(DEMO_INVESTIGATIONS);
  return { data, origin: 'demo', retrievedAt: new Date().toISOString(), source: 'Demo Adapter' };
}

export async function getInvestigation(id: string): Promise<Sourced<Investigation | null>> {
  const data = await delay(DEMO_INVESTIGATIONS.find(i => i.id === id) ?? null);
  return { data, origin: 'demo', retrievedAt: new Date().toISOString(), source: 'Demo Adapter' };
}
