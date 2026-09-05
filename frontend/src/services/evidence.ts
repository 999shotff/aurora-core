import type { EvidenceItem, Sourced } from '../types/domain';

const DEMO_EVIDENCE: EvidenceItem[] = [
  {
    id: 'ev_01', investigationId: 'inv_02', title: 'Sentinel-2 scene, AOI-7',
    description: 'True-color and NDVI composite over AOI-7, cloud coverage 4.2%.',
    sourceType: 'satellite', source: 'Sentinel-2 L2A', timestamp: '2026-08-31T10:12:00Z',
    confidence: 'high', status: 'corroborated',
    metadata: { resolution: '10m', bands: 'B02 B03 B04 B08', cloudCoverage: '4.2%', derived: 'NDVI, NDWI' },
  },
  {
    id: 'ev_02', investigationId: 'inv_02', title: 'Prior manual survey, AOI-7',
    description: 'Field survey notes from the previous quarter used as a baseline comparison.',
    sourceType: 'document', source: 'Field Report Q2-2026', timestamp: '2026-06-02T00:00:00Z',
    confidence: 'medium', status: 'corroborated', metadata: { author: 'Field team', pages: '4' },
  },
  {
    id: 'ev_03', investigationId: 'inv_01', title: 'BTC-USD realized volatility, 90d',
    description: 'Derived realized volatility series computed from OHLCV bars.',
    sourceType: 'derived-metric', source: 'Aurora Market Service', timestamp: '2026-09-02T08:00:00Z',
    confidence: 'medium', status: 'unverified', metadata: { window: '90d', method: 'close-to-close' },
  },
  {
    id: 'ev_04', investigationId: 'inv_01', title: 'Post-halving volume anomaly',
    description: 'Volume spike flagged 6 days after the most recent halving event.',
    sourceType: 'market-data', source: 'Aurora Market Service', timestamp: '2026-08-20T14:30:00Z',
    confidence: 'low', status: 'contested', metadata: { asset: 'BTC-USD', magnitude: '+240% vs 30d avg' },
  },
  {
    id: 'ev_05', investigationId: 'inv_04', title: 'Classifier disagreement log', description: 'Cases where the automated classifier output diverged from manual review labels.',
    sourceType: 'derived-metric', source: 'Aurora Geo Service', timestamp: '2026-07-15T09:00:00Z',
    confidence: 'high', status: 'corroborated', metadata: { disagreementRate: '3.8%', sampleSize: '1,204 tiles' },
  },
];

function delay<T>(value: T, ms = 220): Promise<T> {
  return new Promise(resolve => setTimeout(() => resolve(value), ms));
}

export async function listEvidence(investigationId?: string): Promise<Sourced<EvidenceItem[]>> {
  const data = await delay(investigationId ? DEMO_EVIDENCE.filter(e => e.investigationId === investigationId) : DEMO_EVIDENCE);
  return { data, origin: 'demo', retrievedAt: new Date().toISOString(), source: 'Demo Adapter' };
}

export async function getEvidence(id: string): Promise<Sourced<EvidenceItem | null>> {
  const data = await delay(DEMO_EVIDENCE.find(e => e.id === id) ?? null);
  return { data, origin: 'demo', retrievedAt: new Date().toISOString(), source: 'Demo Adapter' };
}
