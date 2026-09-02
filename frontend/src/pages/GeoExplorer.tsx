import React, { useState, useCallback } from 'react';
import { API_BASE } from '../services/config';

type IntegrityState = 'DATA_AVAILABLE' | 'DATA_STALE' | 'DATA_UNAVAILABLE' | 'LOW_CONFIDENCE' | 'INSUFFICIENT_RESOLUTION' | 'INSUFFICIENT_TEMPORAL_COVERAGE' | 'PROCESSING_FAILED' | 'PROVIDER_ERROR';

interface GeoScene {
  scene_id: string;
  provider: string;
  dataset: string;
  acquisition_time: string;
  cloud_pct: number;
  resolution_m: number;
  bands: string[];
  quality_grade: string;
  thumbnail_url: string;
}

interface GeoAOI {
  name: string;
  south: number;
  west: number;
  north: number;
  east: number;
  area_km2: number;
}

interface SearchResult {
  scenes: GeoScene[];
  total_count: number;
  aoi: GeoAOI;
  date_range: { start: string; end: string };
}

interface ChangeResult {
  change_detected: boolean;
  change_type?: string;
  feature?: string;
  magnitude?: number;
  confidence?: number;
  integrity_state: IntegrityState;
  uncertainty?: string;
  notes?: string[];
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#010409', color: '#c9d1d9', fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", lineHeight: 1.6 },
  container: { maxWidth: '1400px', margin: '0 auto', padding: '0 24px' },
  header: { position: 'sticky', top: 0, zIndex: 50, background: 'rgba(1, 4, 9, 0.85)', backdropFilter: 'blur(12px)', borderBottom: '1px solid #21262d', padding: '16px 0' },
  headerInner: { maxWidth: '1400px', margin: '0 auto', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  logo: { fontSize: '20px', fontWeight: 700, color: '#e6edf3', letterSpacing: '2px', textTransform: 'uppercase' as const },
  logoAccent: { color: '#26a69a' },
  headerTag: { fontSize: '13px', color: '#8b949e', padding: '4px 12px', border: '1px solid #21262d', borderRadius: '6px' },
  main: { padding: '32px 0', display: 'grid', gridTemplateColumns: '380px 1fr', gap: '24px' },
  panel: { background: 'rgba(13, 17, 23, 0.6)', border: '1px solid #21262d', borderRadius: '14px', padding: '24px' },
  panelTitle: { fontSize: '16px', fontWeight: 600, color: '#e6edf3', marginBottom: '20px' },
  field: { marginBottom: '16px' },
  label: { fontSize: '12px', fontWeight: 600, color: '#8b949e', textTransform: 'uppercase' as const, letterSpacing: '0.5px', marginBottom: '6px', display: 'block' },
  select: { width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #30363d', background: '#0d1117', color: '#c9d1d9', fontSize: '14px', outline: 'none' },
  input: { width: '100%', padding: '10px 12px', borderRadius: '8px', border: '1px solid #30363d', background: '#0d1117', color: '#c9d1d9', fontSize: '14px', outline: 'none', boxSizing: 'border-box' as const },
  button: { width: '100%', padding: '12px', borderRadius: '8px', border: 'none', background: '#238636', color: '#fff', fontSize: '14px', fontWeight: 600, cursor: 'pointer', marginTop: '8px' },
  buttonDisabled: { opacity: 0.5, cursor: 'not-allowed' },
  buttonSecondary: { width: '100%', padding: '12px', borderRadius: '8px', border: '1px solid #30363d', background: 'transparent', color: '#c9d1d9', fontSize: '14px', fontWeight: 600, cursor: 'pointer', marginTop: '8px' },
  tabBar: { display: 'flex', gap: '8px', marginBottom: '20px' },
  tab: { padding: '8px 16px', borderRadius: '8px', border: '1px solid #21262d', background: 'transparent', color: '#8b949e', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  tabActive: { background: 'rgba(38, 166, 154, 0.15)', color: '#26a69a', border: '1px solid rgba(38, 166, 154, 0.4)' },
  sceneCard: { background: 'rgba(1, 4, 9, 0.6)', border: '1px solid #21262d', borderRadius: '10px', padding: '16px', marginBottom: '12px', cursor: 'pointer', transition: 'border-color 0.2s' },
  sceneCardSelected: { border: '1px solid #26a69a', background: 'rgba(38, 166, 154, 0.05)' },
  sceneHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' },
  sceneId: { fontSize: '13px', fontWeight: 600, color: '#26a69a' },
  sceneMeta: { fontSize: '12px', color: '#8b949e' },
  badge: { display: 'inline-block', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 700, letterSpacing: '0.5px' },
  metricGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '12px', marginBottom: '16px' },
  metricCard: { background: 'rgba(1, 4, 9, 0.6)', border: '1px solid #21262d', borderRadius: '10px', padding: '14px' },
  metricValue: { fontSize: '18px', fontWeight: 700, color: '#26a69a', marginBottom: '2px' },
  metricLabel: { fontSize: '11px', color: '#8b949e' },
  placeholder: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '200px', border: '2px dashed #21262d', borderRadius: '12px', color: '#484f58', fontSize: '14px' },
  backLink: { fontSize: '13px', color: '#58a6ff', textDecoration: 'none', cursor: 'pointer', marginBottom: '16px', display: 'inline-block' },
  disclaimer: { background: 'rgba(240, 136, 62, 0.08)', border: '1px solid rgba(240, 136, 62, 0.3)', borderRadius: '10px', padding: '16px 20px', marginBottom: '24px', fontSize: '13px', color: '#c9d1d9' },
  providerBadge: { display: 'inline-block', padding: '2px 8px', borderRadius: '4px', fontSize: '10px', fontWeight: 700, marginRight: '6px' },
  coordRow: { display: 'flex', gap: '12px' },
  mapPlaceholder: { width: '100%', height: '200px', background: '#0d1117', border: '1px solid #21262d', borderRadius: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#484f58', fontSize: '13px', marginBottom: '16px' },
};

function fmtCloud(pct: number): string { return pct.toFixed(1) + '%'; }
function fmtRes(m: number): string { return m < 1 ? (m * 1000).toFixed(0) + 'm' : m.toFixed(0) + 'm'; }

function IntegrityBadge({ state }: { state: IntegrityState }) {
  const colors: Record<string, string> = {
    DATA_AVAILABLE: '#3fb950',
    DATA_STALE: '#e3b341',
    DATA_UNAVAILABLE: '#f85149',
    LOW_CONFIDENCE: '#f0883e',
    INSUFFICIENT_RESOLUTION: '#f0883e',
    INSUFFICIENT_TEMPORAL_COVERAGE: '#f0883e',
    PROCESSING_FAILED: '#f85149',
    PROVIDER_ERROR: '#f85149',
  };
  const c = colors[state] || '#8b949e';
  return <span style={{ ...styles.badge, background: `${c}20`, color: c, border: `1px solid ${c}40` }}>{state.replace(/_/g, ' ')}</span>;
}

function SceneCard({ scene, selected, onClick }: { scene: GeoScene; selected: boolean; onClick: () => void }) {
  const qualityColor = scene.quality_grade === 'GOOD' ? '#3fb950' : scene.quality_grade === 'PARTIAL' ? '#e3b341' : '#f85149';
  return (
    <div
      style={{ ...styles.sceneCard, ...(selected ? styles.sceneCardSelected : {}) }}
      onClick={onClick}
      onMouseEnter={(e) => { if (!selected) (e.currentTarget as HTMLDivElement).style.borderColor = '#30363d'; }}
      onMouseLeave={(e) => { if (!selected) (e.currentTarget as HTMLDivElement).style.borderColor = '#21262d'; }}
    >
      <div style={styles.sceneHeader}>
        <span style={styles.sceneId}>{scene.scene_id.slice(0, 24)}</span>
        <span style={{ ...styles.badge, background: `${qualityColor}20`, color: qualityColor, border: `1px solid ${qualityColor}40` }}>{scene.quality_grade}</span>
      </div>
      <div style={styles.sceneMeta}>
        {scene.dataset} — {new Date(scene.acquisition_time).toLocaleDateString()}
      </div>
      <div style={{ ...styles.sceneMeta, marginTop: '4px' }}>
        Cloud: {fmtCloud(scene.cloud_pct)} · Res: {fmtRes(scene.resolution_m)} · Bands: {scene.bands.length}
      </div>
    </div>
  );
}

const PRESET_AOIS: Record<string, { south: number; west: number; north: number; east: number }> = {
  'Port of Los Angeles': { south: 33.72, west: -118.35, north: 33.80, east: -118.20 },
  'Sahel Region': { south: 12.0, west: -5.0, north: 16.0, east: 5.0 },
  'Great Barrier Reef': { south: -18.5, east: 147.5, north: -14.5, west: 146.5 },
  'Nile Delta': { south: 29.5, east: 32.5, north: 31.5, west: 29.5 },
  'Amazon Basin': { south: -5.0, west: -65.0, north: 0.0, east: -55.0 },
};

const GeoExplorer: React.FC = () => {
  const [aoiName, setAoiName] = useState('Port of Los Angeles');
  const [south, setSouth] = useState('33.72');
  const [west, setWest] = useState('-118.35');
  const [north, setNorth] = useState('33.80');
  const [east, setEast] = useState('-118.20');
  const [startDate, setStartDate] = useState('2025-06-01');
  const [endDate, setEndDate] = useState('2025-06-30');
  const [maxCloud, setMaxCloud] = useState(30);
  const [provider, setProvider] = useState('');
  const [dataset, setDataset] = useState('');
  const [searchResult, setSearchResult] = useState<SearchResult | null>(null);
  const [selectedScene, setSelectedScene] = useState<GeoScene | null>(null);
  const [changeResult, setChangeResult] = useState<ChangeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'scenes' | 'change' | 'provenance'>('scenes');

  const handlePreset = (name: string) => {
    const preset = PRESET_AOIS[name];
    if (preset) {
      setAoiName(name);
      setSouth(String(preset.south));
      setWest(String(preset.west));
      setNorth(String(preset.north));
      setEast(String(preset.east));
    }
  };

  const handleSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const body: Record<string, unknown> = {
        aoi_name: aoiName,
        south: parseFloat(south),
        west: parseFloat(west),
        north: parseFloat(north),
        east: parseFloat(east),
        start_date: startDate,
        end_date: endDate,
        max_cloud_pct: maxCloud,
      };
      if (provider) body.provider = provider;
      if (dataset) body.dataset = dataset;

      const resp = await fetch(`${API_BASE}/api/v1/geo/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!resp.ok) {
        const errBody = await resp.json().catch(() => ({}));
        throw new Error(errBody.detail || `HTTP ${resp.status}`);
      }
      const data: SearchResult = await resp.json();
      setSearchResult(data);
      setSelectedScene(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [aoiName, south, west, north, east, startDate, endDate, maxCloud, provider, dataset]);

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <span style={styles.logo}>AURORA <span style={styles.logoAccent}>GEO</span></span>
          <span style={styles.headerTag}>Earth Observation Research</span>
        </div>
      </header>

      <main style={styles.container}>
        <a style={styles.backLink} href="/">← Back to Dashboard</a>

        <div style={styles.disclaimer}>
          <strong style={{ color: '#f0883e' }}>EXPERIMENTAL — Research Evidence Only</strong>
          <br />
          Satellite observations are research evidence and are NOT guaranteed predictions.
          No targeting. No person identification. All data retains full provenance.
        </div>

        <div style={styles.main}>
          <div>
            <div style={styles.panel}>
              <div style={styles.panelTitle}>Area of Interest</div>

              <div style={styles.mapPlaceholder}>
                AOI: {aoiName} ({parseFloat(south).toFixed(2)}°, {parseFloat(west).toFixed(2)}°) → ({parseFloat(north).toFixed(2)}°, {parseFloat(east).toFixed(2)}°)
                <br />Area: ~{(
                  Math.abs(parseFloat(north) - parseFloat(south)) * 111.32 *
                  Math.abs(parseFloat(east) - parseFloat(west)) * 111.32 *
                  Math.cos(((parseFloat(south) + parseFloat(north)) / 2) * Math.PI / 180)
                ).toFixed(0)} km²
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Preset Locations</label>
                <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                  {Object.keys(PRESET_AOIS).map(name => (
                    <button
                      key={name}
                      style={{ ...styles.tab, fontSize: '11px', padding: '4px 10px' }}
                      onClick={() => handlePreset(name)}
                    >{name}</button>
                  ))}
                </div>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>AOI Name</label>
                <input style={styles.input} value={aoiName} onChange={e => setAoiName(e.target.value)} />
              </div>

              <div style={styles.coordRow}>
                <div style={styles.field}>
                  <label style={styles.label}>South</label>
                  <input style={styles.input} type="number" step="0.01" value={south} onChange={e => setSouth(e.target.value)} />
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>West</label>
                  <input style={styles.input} type="number" step="0.01" value={west} onChange={e => setWest(e.target.value)} />
                </div>
              </div>
              <div style={styles.coordRow}>
                <div style={styles.field}>
                  <label style={styles.label}>North</label>
                  <input style={styles.input} type="number" step="0.01" value={north} onChange={e => setNorth(e.target.value)} />
                </div>
                <div style={styles.field}>
                  <label style={styles.label}>East</label>
                  <input style={styles.input} type="number" step="0.01" value={east} onChange={e => setEast(e.target.value)} />
                </div>
              </div>

              <hr style={{ border: 'none', borderTop: '1px solid #21262d', margin: '16px 0' }} />

              <div style={styles.field}>
                <label style={styles.label}>Date Range</label>
                <div style={styles.coordRow}>
                  <input style={styles.input} type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
                  <input style={styles.input} type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
                </div>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Max Cloud Cover ({maxCloud}%)</label>
                <input style={{ width: '100%', accentColor: '#26a69a' }} type="range" min="0" max="100" step="5" value={maxCloud} onChange={e => setMaxCloud(Number(e.target.value))} />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Provider</label>
                <select style={styles.select} value={provider} onChange={e => setProvider(e.target.value)}>
                  <option value="">All Providers</option>
                  <option value="copernicus_sentinel">Copernicus Sentinel</option>
                  <option value="nasa_gibs">NASA GIBS</option>
                  <option value="skyfi">SkyFi (Optional)</option>
                </select>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Dataset</label>
                <select style={styles.select} value={dataset} onChange={e => setDataset(e.target.value)}>
                  <option value="">Auto</option>
                  <option value="S2L2A">Sentinel-2 L2A</option>
                  <option value="S2L1C">Sentinel-2 L1C</option>
                  <option value="S1GRD">Sentinel-1 GRD</option>
                  <option value="MODIS_Terra_CorrectedReflectance_TrueColor">MODIS Terra</option>
                </select>
              </div>

              <button
                style={{ ...styles.button, ...(loading ? styles.buttonDisabled : {}) }}
                onClick={handleSearch}
                disabled={loading}
              >
                {loading ? 'Searching...' : 'Search Scenes'}
              </button>

              {error && (
                <div style={{ color: '#f85149', fontSize: '13px', marginTop: '12px' }}>{error}</div>
              )}
            </div>
          </div>

          <div>
            {!searchResult && !loading && (
              <div style={styles.placeholder}>Configure an AOI and search for satellite scenes</div>
            )}

            {loading && <div style={styles.placeholder}>Searching satellite catalogs...</div>}

            {searchResult && (
              <>
                <div style={styles.metricGrid}>
                  <div style={styles.metricCard}>
                    <div style={styles.metricValue}>{searchResult.total_count}</div>
                    <div style={styles.metricLabel}>Scenes Found</div>
                  </div>
                  <div style={styles.metricCard}>
                    <div style={styles.metricValue}>{searchResult.aoi.area_km2.toFixed(0)} km²</div>
                    <div style={styles.metricLabel}>AOI Area</div>
                  </div>
                </div>

                <div style={styles.panel}>
                  <div style={styles.tabBar}>
                    <button style={{ ...styles.tab, ...(activeTab === 'scenes' ? styles.tabActive : {}) }} onClick={() => setActiveTab('scenes')}>
                      Scenes ({searchResult.scenes.length})
                    </button>
                    <button style={{ ...styles.tab, ...(activeTab === 'change' ? styles.tabActive : {}) }} onClick={() => setActiveTab('change')}>
                      Change Detection
                    </button>
                    <button style={{ ...styles.tab, ...(activeTab === 'provenance' ? styles.tabActive : {}) }} onClick={() => setActiveTab('provenance')}>
                      Provenance
                    </button>
                  </div>

                  {activeTab === 'scenes' && (
                    <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                      {searchResult.scenes.length === 0 ? (
                        <div style={styles.placeholder}>No scenes found for this AOI/date range</div>
                      ) : (
                        searchResult.scenes.map(scene => (
                          <SceneCard
                            key={scene.scene_id}
                            scene={scene}
                            selected={selectedScene?.scene_id === scene.scene_id}
                            onClick={() => setSelectedScene(scene)}
                          />
                        ))
                      )}
                    </div>
                  )}

                  {activeTab === 'change' && (
                    <div>
                      {changeResult ? (
                        <div>
                          <div style={styles.metricGrid}>
                            <div style={styles.metricCard}>
                              <div style={{ ...styles.metricValue, color: changeResult.change_detected ? '#f0883e' : '#3fb950' }}>
                                {changeResult.change_detected ? 'CHANGE DETECTED' : 'NO CHANGE'}
                              </div>
                              <div style={styles.metricLabel}>Result</div>
                            </div>
                            <div style={styles.metricCard}>
                              <div style={styles.metricValue}>{changeResult.confidence != null ? (changeResult.confidence * 100).toFixed(0) + '%' : 'N/A'}</div>
                              <div style={styles.metricLabel}>Confidence</div>
                            </div>
                          </div>
                          <IntegrityBadge state={changeResult.integrity_state} />
                          {changeResult.uncertainty && (
                            <div style={{ fontSize: '12px', color: '#8b949e', marginTop: '12px', padding: '12px', background: 'rgba(1,4,9,0.4)', borderRadius: '8px' }}>
                              <strong>Uncertainty:</strong> {changeResult.uncertainty}
                            </div>
                          )}
                        </div>
                      ) : (
                        <div style={styles.placeholder}>Select two scenes to compare for change detection</div>
                      )}
                    </div>
                  )}

                  {activeTab === 'provenance' && selectedScene && (
                    <div>
                      <div style={styles.metricGrid}>
                        <div style={styles.metricCard}>
                          <div style={styles.metricValue}>{selectedScene.provider}</div>
                          <div style={styles.metricLabel}>Provider</div>
                        </div>
                        <div style={styles.metricCard}>
                          <div style={styles.metricValue}>{selectedScene.dataset}</div>
                          <div style={styles.metricLabel}>Dataset</div>
                        </div>
                      </div>
                      <div style={{ fontSize: '13px', color: '#c9d1d9', lineHeight: 1.8 }}>
                        <div><strong>Scene ID:</strong> {selectedScene.scene_id}</div>
                        <div><strong>Acquired:</strong> {new Date(selectedScene.acquisition_time).toISOString()}</div>
                        <div><strong>Resolution:</strong> {fmtRes(selectedScene.resolution_m)}</div>
                        <div><strong>Bands:</strong> {selectedScene.bands.join(', ') || 'N/A'}</div>
                        <div><strong>Cloud Cover:</strong> {fmtCloud(selectedScene.cloud_pct)}</div>
                        <div><strong>Quality:</strong> {selectedScene.quality_grade}</div>
                      </div>
                    </div>
                  )}
                </div>
              </>
            )}
          </div>
        </div>
      </main>
    </div>
  );
};

export { GeoExplorer };
