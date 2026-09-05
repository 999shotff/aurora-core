import type { ReportRecord, Sourced } from '../types/domain';

const DEMO_REPORTS: ReportRecord[] = [
  {
    id: 'rep_01', title: 'AOI-7 vegetation change — quarterly findings', investigationId: 'inv_02',
    author: 'Aurora Research Workspace', generatedAt: '2026-09-01T17:00:00Z',
    executiveSummary: 'Comparison of Q2 and Q3 Sentinel-2 composites shows a localized reduction in vegetation index across the northern third of AOI-7, corroborated by the prior field survey.',
    findingsCount: 5, confidence: 'high', format: 'pdf',
  },
  {
    id: 'rep_02', title: 'BTC-USD volatility regime — interim note', investigationId: 'inv_01',
    author: 'Aurora Research Workspace', generatedAt: '2026-09-02T12:00:00Z',
    executiveSummary: 'Realized volatility has not yet shown a statistically robust structural break; the post-halving volume anomaly remains contested pending a longer observation window.',
    findingsCount: 3, confidence: 'medium', format: 'md',
  },
  {
    id: 'rep_03', title: 'AOI-3 classifier disagreement audit', investigationId: 'inv_04',
    author: 'Aurora Geo Service', generatedAt: '2026-07-18T15:00:00Z',
    executiveSummary: 'Automated land-use classification disagreed with manual labels on 3.8% of sampled tiles, concentrated in mixed-use boundary zones.',
    findingsCount: 8, confidence: 'high', format: 'csv',
  },
];

function delay<T>(value: T, ms = 220): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(value), ms));
}

export async function listReports(): Promise<Sourced<ReportRecord[]>> {
  const data = await delay(DEMO_REPORTS);
  return { data, origin: 'demo', retrievedAt: new Date().toISOString(), source: 'Demo Adapter' };
}
