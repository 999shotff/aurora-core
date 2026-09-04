import React, { useState, useCallback, useEffect, useRef } from 'react';
import { API_BASE } from '../services/config';

type IntegrityState = 'DATA_AVAILABLE' | 'DATA_STALE' | 'DATA_UNAVAILABLE' | 'LOW_CONFIDENCE' | 'INSUFFICIENT_RESOLUTION' | 'INSUFFICIENT_TEMPORAL_COVERAGE' | 'PROCESSING_FAILED' | 'PROVIDER_ERROR';
type ViewMode = '2d' | '3d';
type ActivePanel = 'scenes' | 'indices' | 'change' | 'timeseries' | 'provenance';

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
  metadata_url: string;
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

interface IndexResult {
  name: string;
  supported: boolean;
  mean: number;
  std: number;
  min_val: number;
  max_val: number;
  valid_count: number;
  total_count: number;
  formula: string;
  source_bands: string[];
  uncertainty: string;
  integrity_state: IntegrityState;
}

interface ChangeResult {
  change_detected: boolean;
  change_type?: string;
  feature?: string;
  magnitude?: number;
  confidence?: number;
  changed_area_km2?: number;
  spatial_extent_pct?: number;
  integrity_state: IntegrityState;
  uncertainty?: string;
}

interface TimeSeriesPoint {
  date: string;
  scene_id: string;
  value: number;
  cloud_pct: number;
  confidence: number;
  integrity_state: string;
}

interface TimeSeriesResult {
  index: string;
  provider: string;
  observations: TimeSeriesPoint[];
  statistics: {
    count: number;
    mean: number;
    median: number;
    stdev: number;
    min: number;
    max: number;
  } | null;
  total_scenes_found: number;
  uncertainty: string;
}

const styles: Record<string, React.CSSProperties> = {
  page: { minHeight: '100vh', background: '#010409', color: '#c9d1d9', fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif", lineHeight: 1.6 },
  container: { maxWidth: '1600px', margin: '0 auto', padding: '0 24px' },
  header: { position: 'sticky', top: 0, zIndex: 50, background: 'rgba(1, 4, 9, 0.85)', backdropFilter: 'blur(12px)', borderBottom: '1px solid #21262d', padding: '16px 0' },
  headerInner: { maxWidth: '1600px', margin: '0 auto', padding: '0 24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  logo: { fontSize: '20px', fontWeight: 700, color: '#e6edf3', letterSpacing: '2px', textTransform: 'uppercase' as const },
  logoAccent: { color: '#26a69a' },
  headerTag: { fontSize: '13px', color: '#8b949e', padding: '4px 12px', border: '1px solid #21262d', borderRadius: '6px' },
  headerControls: { display: 'flex', gap: '8px', alignItems: 'center' },
  viewToggle: { display: 'flex', borderRadius: '8px', border: '1px solid #30363d', overflow: 'hidden' },
  viewBtn: { padding: '6px 14px', border: 'none', background: 'transparent', color: '#8b949e', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  viewBtnActive: { padding: '6px 14px', border: 'none', background: 'rgba(38, 166, 154, 0.2)', color: '#26a69a', fontSize: '12px', fontWeight: 600, cursor: 'pointer' },
  main: { padding: '24px 0', display: 'grid', gridTemplateColumns: '360px 1fr 320px', gap: '20px', minHeight: 'calc(100vh - 120px)' },
  panel: { background: 'rgba(13, 17, 23, 0.6)', border: '1px solid #21262d', borderRadius: '14px', padding: '20px' },
  panelTitle: { fontSize: '15px', fontWeight: 600, color: '#e6edf3', marginBottom: '16px' },
  field: { marginBottom: '14px' },
  label: { fontSize: '11px', fontWeight: 600, color: '#8b949e', textTransform: 'uppercase' as const, letterSpacing: '0.5px', marginBottom: '5px', display: 'block' },
  select: { width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #30363d', background: '#0d1117', color: '#c9d1d9', fontSize: '13px', outline: 'none' },
  input: { width: '100%', padding: '8px 10px', borderRadius: '6px', border: '1px solid #30363d', background: '#0d1117', color: '#c9d1d9', fontSize: '13px', outline: 'none', boxSizing: 'border-box' as const },
  button: { width: '100%', padding: '10px', borderRadius: '8px', border: 'none', background: '#238636', color: '#fff', fontSize: '13px', fontWeight: 600, cursor: 'pointer', marginTop: '8px' },
  buttonDisabled: { opacity: 0.5, cursor: 'not-allowed' },
  buttonSmall: { padding: '6px 12px', borderRadius: '6px', border: '1px solid #30363d', background: 'transparent', color: '#c9d1d9', fontSize: '11px', fontWeight: 600, cursor: 'pointer' },
  tabBar: { display: 'flex', gap: '6px', marginBottom: '16px', flexWrap: 'wrap' as const },
  tab: { padding: '6px 12px', borderRadius: '6px', border: '1px solid #21262d', background: 'transparent', color: '#8b949e', fontSize: '11px', fontWeight: 600, cursor: 'pointer', whiteSpace: 'nowrap' as const },
  tabActive: { background: 'rgba(38, 166, 154, 0.15)', color: '#26a69a', border: '1px solid rgba(38, 166, 154, 0.4)' },
  sceneCard: { background: 'rgba(1, 4, 9, 0.6)', border: '1px solid #21262d', borderRadius: '8px', padding: '12px', marginBottom: '8px', cursor: 'pointer', transition: 'border-color 0.2s', fontSize: '12px' },
  sceneCardSelected: { border: '1px solid #26a69a', background: 'rgba(38, 166, 154, 0.05)' },
  sceneHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' },
  sceneId: { fontSize: '12px', fontWeight: 600, color: '#26a69a', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' as const, maxWidth: '200px' },
  badge: { display: 'inline-block', padding: '2px 6px', borderRadius: '4px', fontSize: '9px', fontWeight: 700, letterSpacing: '0.5px' },
  metricGrid: { display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginBottom: '14px' },
  metricCard: { background: 'rgba(1, 4, 9, 0.6)', border: '1px solid #21262d', borderRadius: '8px', padding: '12px' },
  metricValue: { fontSize: '16px', fontWeight: 700, color: '#26a69a', marginBottom: '2px' },
  metricLabel: { fontSize: '10px', color: '#8b949e' },
  placeholder: { display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', border: '2px dashed #21262d', borderRadius: '12px', color: '#484f58', fontSize: '13px', minHeight: '300px' },
  mapContainer: { width: '100%', height: '100%', minHeight: '500px', borderRadius: '12px', overflow: 'hidden', background: '#0d1117', position: 'relative' as const },
  backLink: { fontSize: '13px', color: '#58a6ff', textDecoration: 'none', cursor: 'pointer', marginBottom: '12px', display: 'inline-block' },
  disclaimer: { background: 'rgba(240, 136, 62, 0.08)', border: '1px solid rgba(240, 136, 62, 0.3)', borderRadius: '8px', padding: '12px 16px', marginBottom: '20px', fontSize: '12px', color: '#c9d1d9' },
  coordRow: { display: 'flex', gap: '10px' },
  indexResult: { background: 'rgba(1, 4, 9, 0.6)', border: '1px solid #21262d', borderRadius: '8px', padding: '12px', marginBottom: '10px' },
  indexHeader: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' },
  indexName: { fontSize: '13px', fontWeight: 600, color: '#26a69a' },
  indexValue: { fontSize: '18px', fontWeight: 700, color: '#e6edf3' },
  timePoint: { display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid rgba(33, 38, 45, 0.5)', fontSize: '12px' },
};

function fmtCloud(pct: number): string { return pct.toFixed(1) + '%'; }
function fmtRes(m: number): string { return m < 1 ? (m * 1000).toFixed(0) + 'm' : m.toFixed(0) + 'm'; }
function fmtVal(v: number): string { return isNaN(v) ? 'N/A' : v.toFixed(4); }

function IntegrityBadge({ state }: { state: IntegrityState }) {
  const c = { DATA_AVAILABLE: '#3fb950', DATA_STALE: '#e3b341', DATA_UNAVAILABLE: '#f85149', LOW_CONFIDENCE: '#f0883e', INSUFFICIENT_RESOLUTION: '#f0883e', INSUFFICIENT_TEMPORAL_COVERAGE: '#f0883e', PROCESSING_FAILED: '#f85149', PROVIDER_ERROR: '#f85149' }[state] || '#8b949e';
  return <span style={{ ...styles.badge, background: `${c}20`, color: c, border: `1px solid ${c}40` }}>{state.replace(/_/g, ' ')}</span>;
}

const PRESET_AOIS: Record<string, { south: number; west: number; north: number; east: number }> = {
  'Port of Los Angeles': { south: 33.72, west: -118.35, north: 33.80, east: -118.20 },
  'Sahel Region': { south: 12.0, west: -5.0, north: 16.0, east: 5.0 },
  'Great Barrier Reef': { south: -18.5, east: 147.5, north: -14.5, west: 146.5 },
  'Nile Delta': { south: 29.5, east: 32.5, north: 31.5, west: 29.5 },
  'Amazon Basin': { south: -5.0, west: -65.0, north: 0.0, east: -55.0 },
  'Custom': { south: 0, west: 0, north: 1, east: 1 },
};

const GeoExplorer: React.FC = () => {
  const [viewMode, setViewMode] = useState<ViewMode>('2d');
  const [activePanel, setActivePanel] = useState<ActivePanel>('scenes');
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
  const [selectedScenes, setSelectedScenes] = useState<GeoScene[]>([]);
  const [indices, setIndices] = useState<IndexResult[]>([]);
  const [changeResult, setChangeResult] = useState<ChangeResult | null>(null);
  const [timeSeries, setTimeSeries] = useState<TimeSeriesResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [processingIndex, setProcessingIndex] = useState(false);
  const [loadingTimeSeries, setLoadingTimeSeries] = useState(false);
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<unknown>(null);
  const globeRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (viewMode === '2d' && mapRef.current && !mapInstanceRef.current) {
      const L = (window as Record<string, unknown>).L;
      if (!L) {
        const link = document.createElement('link');
        link.rel = 'stylesheet';
        link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
        document.head.appendChild(link);
        const script = document.createElement('script');
        script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
        script.onload = () => initMap();
        document.head.appendChild(script);
      } else {
        initMap();
      }
    }
    function initMap() {
      const L = (window as Record<string, unknown>).L as Record<string, unknown>;
      if (!L || !mapRef.current || mapInstanceRef.current) return;
      const centerLat = (parseFloat(south) + parseFloat(north)) / 2;
      const centerLng = (parseFloat(west) + parseFloat(east)) / 2;
      const map = (L as { map: (el: HTMLElement, opts: Record<string, unknown>) => unknown }).map(mapRef.current, {
        center: [centerLat, centerLng],
        zoom: 8,
        zoomControl: true,
        attributionControl: false,
      });
      (L as { tileLayer: (url: string, opts: Record<string, unknown>) => { addTo: (m: unknown) => unknown } }).tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 18,
      }).addTo(map);
      mapInstanceRef.current = map;
    }
  }, [viewMode, south, west, north, east]);

  useEffect(() => {
    if (viewMode === '3d' && globeRef.current && !(window as Record<string, unknown>)._auroraGlobeReady) {
      const script = document.createElement('script');
      script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
      script.onload = () => {
        setTimeout(() => {
          if ((window as Record<string, unknown>)._auroraGlobeReady) return;
          const container = globeRef.current;
          if (!container) return;
          const w = container.clientWidth;
          const h = container.clientHeight;
          const scene = new (window as Record<string, unknown>).THREE.Scene();
          (scene as Record<string, unknown>).background = new (window as Record<string, unknown>).THREE.Color(0x000011);
          const camera = new (window as Record<string, unknown>).THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
          (camera as Record<string, unknown>).position.z = 2.5;
          const renderer = new (window as Record<string, unknown>).THREE.WebGLRenderer({ antialias: true });
          (renderer as Record<string, unknown>).setSize(w, h);
          (renderer as Record<string, unknown>).setPixelRatio(window.devicePixelRatio);
          container.appendChild((renderer as Record<string, unknown>).domElement);
          const earthGeo = new (window as Record<string, unknown>).THREE.SphereGeometry(1, 64, 64);
          const earthMat = new (window as Record<string, unknown>).THREE.MeshPhongMaterial({ color: 0x224488, emissive: 0x112244, specular: 0x444444, shininess: 25 });
          const earth = new (window as Record<string, unknown>).THREE.Mesh(earthGeo, earthMat);
          (scene as Record<string, unknown>).add(earth);
          const wireGeo = new (window as Record<string, unknown>).THREE.SphereGeometry(1.001, 32, 32);
          const wireMat = new (window as Record<string, unknown>).THREE.MeshBasicMaterial({ color: 0x26a69a, wireframe: true, transparent: true, opacity: 0.08 });
          const wire = new (window as Record<string, unknown>).THREE.Mesh(wireGeo, wireMat);
          (scene as Record<string, unknown>).add(wire);
          (scene as Record<string, unknown>).add(new (window as Record<string, unknown>).THREE.AmbientLight(0x404040, 0.6));
          const dirLight = new (window as Record<string, unknown>).THREE.DirectionalLight(0xffffff, 0.8);
          (dirLight as Record<string, unknown>).position.set(5, 3, 5);
          (scene as Record<string, unknown>).add(dirLight);
          let dragging = false;
          let prevMouse = { x: 0, y: 0 };
          const canvas = (renderer as Record<string, unknown>).domElement as HTMLElement;
          canvas.addEventListener('mousedown', (e: MouseEvent) => { dragging = true; prevMouse = { x: e.clientX, y: e.clientY }; });
          canvas.addEventListener('mousemove', (e: MouseEvent) => {
            if (!dragging) return;
            (earth as Record<string, unknown>).rotation.y += (e.clientX - prevMouse.x) * 0.005;
            (earth as Record<string, unknown>).rotation.x += (e.clientY - prevMouse.y) * 0.005;
            (wire as Record<string, unknown>).rotation.y = (earth as Record<string, unknown>).rotation.y;
            (wire as Record<string, unknown>).rotation.x = (earth as Record<string, unknown>).rotation.x;
            prevMouse = { x: e.clientX, y: e.clientY };
          });
          canvas.addEventListener('mouseup', () => { dragging = false; });
          canvas.addEventListener('mouseleave', () => { dragging = false; });
          canvas.addEventListener('wheel', (e: WheelEvent) => {
            e.preventDefault();
            const z = (camera as Record<string, unknown>).position as Record<string, number>;
            z.z = Math.max(1.1, Math.min(10, z.z + e.deltaY * 0.001));
          }, { passive: false });
          let touchStart: { x: number; y: number } | null = null;
          canvas.addEventListener('touchstart', (e: TouchEvent) => {
            if (e.touches.length === 1) touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
          });
          canvas.addEventListener('touchmove', (e: TouchEvent) => {
            if (!touchStart || e.touches.length !== 1) return;
            e.preventDefault();
            (earth as Record<string, unknown>).rotation.y += (e.touches[0].clientX - touchStart.x) * 0.005;
            (earth as Record<string, unknown>).rotation.x += (e.touches[0].clientY - touchStart.y) * 0.005;
            (wire as Record<string, unknown>).rotation.y = (earth as Record<string, unknown>).rotation.y;
            (wire as Record<string, unknown>).rotation.x = (earth as Record<string, unknown>).rotation.x;
            touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
          }, { passive: false });
          canvas.addEventListener('touchend', () => { touchStart = null; });
          (window as Record<string, unknown>)._auroraGlobeReady = true;
          const animate = () => {
            requestAnimationFrame(animate);
            (renderer as Record<string, unknown>).render(scene, camera);
          };
          animate();
        }, 100);
      };
      document.head.appendChild(script);
    }
  }, [viewMode]);

  const handlePreset = (name: string) => {
    const p = PRESET_AOIS[name];
    if (p) { setAoiName(name); setSouth(String(p.south)); setWest(String(p.west)); setNorth(String(p.north)); setEast(String(p.east)); }
  };

  const handleSearch = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const body: Record<string, unknown> = { aoi_name: aoiName, south: parseFloat(south), west: parseFloat(west), north: parseFloat(north), east: parseFloat(east), start_date: startDate, end_date: endDate, max_cloud_pct: maxCloud };
      if (provider) body.provider = provider;
      if (dataset) body.dataset = dataset;
      const resp = await fetch(`${API_BASE}/api/v1/geo/search`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!resp.ok) { const errBody = await resp.json().catch(() => ({})); throw new Error(errBody.detail || `HTTP ${resp.status}`); }
      const data: SearchResult = await resp.json();
      setSearchResult(data); setSelectedScenes([]); setIndices([]); setChangeResult(null); setTimeSeries(null);
    } catch (e) { setError(e instanceof Error ? e.message : 'Unknown error'); }
    finally { setLoading(false); }
  }, [aoiName, south, west, north, east, startDate, endDate, maxCloud, provider, dataset]);

  const toggleSceneSelection = (scene: GeoScene) => {
    setSelectedScenes(prev => {
      const exists = prev.find(s => s.scene_id === scene.scene_id);
      if (exists) return prev.filter(s => s.scene_id !== scene.scene_id);
      if (prev.length >= 2) return [prev[1], scene];
      return [...prev, scene];
    });
  };

  const handleComputeIndices = useCallback(async () => {
    if (!searchResult || selectedScenes.length === 0) return;
    setProcessingIndex(true);
    try {
      const results: IndexResult[] = [];
      for (const scene of selectedScenes) {
        for (const idx of ['NDVI', 'NDWI', 'NDBI']) {
          const resp = await fetch(`${API_BASE}/api/v1/geo/observations`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              scene_id: scene.scene_id, provider: scene.provider, dataset: scene.dataset,
              aoi_name: searchResult.aoi.name,
              south: searchResult.aoi.south, west: searchResult.aoi.west,
              north: searchResult.aoi.north, east: searchResult.aoi.east,
              acquisition_time: scene.acquisition_time,
            }),
          });
          if (resp.ok) {
            const obs = await resp.json();
            const bands = obs.bands || scene.bands;
            const hasNIR = bands.includes('B08');
            const hasRED = bands.includes('B04');
            const hasGREEN = bands.includes('B03');
            const hasSWIR = bands.includes('B11');
            const requiredBands: Record<string, boolean> = {
              NDVI: hasNIR && hasRED,
              NDWI: hasGREEN && hasNIR,
              NDBI: hasSWIR && hasNIR,
            };
            const supported = requiredBands[idx] || false;
            const formulas: Record<string, string> = {
              NDVI: '(B08 - B04) / (B08 + B04)',
              NDWI: '(B03 - B08) / (B03 + B08)',
              NDBI: '(B11 - B08) / (B11 + B08)',
            };
            const bandLists: Record<string, string[]> = {
              NDVI: ['B08', 'B04'],
              NDWI: ['B03', 'B08'],
              NDBI: ['B11', 'B08'],
            };
            results.push({
              name: idx,
              supported,
              mean: NaN,
              std: NaN,
              min_val: NaN,
              max_val: NaN,
              valid_count: 0,
              total_count: 0,
              formula: formulas[idx],
              source_bands: bandLists[idx],
              uncertainty: supported
                ? 'Pixel data not available from catalog provider. Index requires actual raster download.'
                : `Required bands not available in ${scene.dataset}`,
              integrity_state: supported ? 'DATA_UNAVAILABLE' : 'DATA_UNAVAILABLE',
            });
          }
        }
      }
      setIndices(results);
    } finally { setProcessingIndex(false); }
  }, [searchResult, selectedScenes]);

  const handleDetectChange = useCallback(async () => {
    if (selectedScenes.length !== 2 || !searchResult) return;
    setLoading(true);
    try {
      const [before, after] = selectedScenes;
      const body = {
        aoi_name: searchResult.aoi.name,
        south: searchResult.aoi.south, west: searchResult.aoi.west,
        north: searchResult.aoi.north, east: searchResult.aoi.east,
        provider: before.provider, dataset: before.dataset,
        before_time: before.acquisition_time, after_time: after.acquisition_time,
        before_bands: before.bands, after_bands: after.bands,
        before_values: {},
        after_values: {},
        feature: 'NDVI', threshold: 0.01,
      };
      const resp = await fetch(`${API_BASE}/api/v1/geo/change-detection`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: ChangeResult = await resp.json();
      setChangeResult(data);
    } catch { setChangeResult({ change_detected: false, integrity_state: 'PROCESSING_FAILED', uncertainty: 'Change detection requires pixel data not available from catalog provider' }); }
    finally { setLoading(false); }
  }, [selectedScenes, searchResult]);

  const handleTimeSeries = useCallback(async () => {
    setLoadingTimeSeries(true);
    try {
      const body = {
        provider: provider || 'nasa_gibs',
        dataset: dataset || 'MODIS_Terra_CorrectedReflectance_TrueColor',
        aoi_name: aoiName,
        south: parseFloat(south), west: parseFloat(west),
        north: parseFloat(north), east: parseFloat(east),
        start_date: startDate, end_date: endDate,
        index: 'NDVI',
        cloud_threshold: maxCloud,
      };
      const resp = await fetch(`${API_BASE}/api/v1/geo/timeseries`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const data: TimeSeriesResult = await resp.json();
      setTimeSeries(data);
    } catch { setTimeSeries(null); }
    finally { setLoadingTimeSeries(false); }
  }, [provider, dataset, aoiName, south, west, north, east, startDate, endDate, maxCloud]);

  const calcArea = () => {
    const s = parseFloat(south), w = parseFloat(west), n = parseFloat(north), e = parseFloat(east);
    if (isNaN(s) || isNaN(w) || isNaN(n) || isNaN(e)) return 0;
    const latRad = ((s + n) / 2) * Math.PI / 180;
    return Math.abs((n - s) * 111.32 * (e - w) * 111.32 * Math.cos(latRad));
  };

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <span style={styles.logo}>AURORA <span style={styles.logoAccent}>GEO</span></span>
          <div style={styles.headerControls}>
            <div style={styles.viewToggle}>
              <button style={viewMode === '2d' ? styles.viewBtnActive : styles.viewBtn} onClick={() => setViewMode('2d')}>2D Map</button>
              <button style={viewMode === '3d' ? styles.viewBtnActive : styles.viewBtn} onClick={() => setViewMode('3d')}>3D Globe</button>
            </div>
            <span style={styles.headerTag}>Earth Observation</span>
          </div>
        </div>
      </header>

      <main style={styles.container}>
        <a style={styles.backLink} href="/">← Dashboard</a>
        <div style={styles.disclaimer}>
          <strong style={{ color: '#f0883e' }}>EXPERIMENTAL — Research Evidence Only.</strong> Satellite observations are NOT predictions. All data retains full provenance. No targeting.
        </div>

        <div style={styles.main}>
          <div>
            <div style={styles.panel}>
              <div style={styles.panelTitle}>Area of Interest</div>
              <div style={{ ...styles.metricCard, marginBottom: '14px' }}>
                <div style={{ fontSize: '12px', color: '#8b949e' }}>AOI: {aoiName}</div>
                <div style={{ fontSize: '11px', color: '#c9d1d9', marginTop: '4px' }}>
                  ({parseFloat(south).toFixed(2)}°, {parseFloat(west).toFixed(2)}°) → ({parseFloat(north).toFixed(2)}°, {parseFloat(east).toFixed(2)}°)
                </div>
                <div style={{ fontSize: '11px', color: '#26a69a', marginTop: '2px' }}>Area: ~{calcArea().toFixed(0)} km²</div>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Presets</label>
                <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                  {Object.keys(PRESET_AOIS).map(name => (
                    <button key={name} style={{ ...styles.buttonSmall, fontSize: '10px', padding: '3px 8px' }} onClick={() => handlePreset(name)}>{name}</button>
                  ))}
                </div>
              </div>

              <div style={styles.coordRow}>
                <div style={styles.field}><label style={styles.label}>South</label><input style={styles.input} type="number" step="0.01" value={south} onChange={e => setSouth(e.target.value)} /></div>
                <div style={styles.field}><label style={styles.label}>West</label><input style={styles.input} type="number" step="0.01" value={west} onChange={e => setWest(e.target.value)} /></div>
              </div>
              <div style={styles.coordRow}>
                <div style={styles.field}><label style={styles.label}>North</label><input style={styles.input} type="number" step="0.01" value={north} onChange={e => setNorth(e.target.value)} /></div>
                <div style={styles.field}><label style={styles.label}>East</label><input style={styles.input} type="number" step="0.01" value={east} onChange={e => setEast(e.target.value)} /></div>
              </div>

              <hr style={{ border: 'none', borderTop: '1px solid #21262d', margin: '12px 0' }} />

              <div style={styles.field}>
                <label style={styles.label}>Date Range</label>
                <div style={styles.coordRow}>
                  <input style={styles.input} type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
                  <input style={styles.input} type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
                </div>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Max Cloud ({maxCloud}%)</label>
                <input style={{ width: '100%', accentColor: '#26a69a' }} type="range" min="0" max="100" step="5" value={maxCloud} onChange={e => setMaxCloud(Number(e.target.value))} />
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Provider</label>
                <select style={styles.select} value={provider} onChange={e => setProvider(e.target.value)}>
                  <option value="">All</option>
                  <option value="copernicus_sentinel">Copernicus Sentinel</option>
                  <option value="nasa_gibs">NASA GIBS</option>
                  <option value="skyfi">SkyFi</option>
                </select>
              </div>

              <div style={styles.field}>
                <label style={styles.label}>Dataset</label>
                <select style={styles.select} value={dataset} onChange={e => setDataset(e.target.value)}>
                  <option value="">Auto</option>
                  <option value="S2L2A">Sentinel-2 L2A</option>
                  <option value="S2L1C">Sentinel-2 L1C</option>
                  <option value="S1GRD">Sentinel-1 GRD</option>
                </select>
              </div>

              <button style={{ ...styles.button, ...(loading ? styles.buttonDisabled : {}) }} onClick={handleSearch} disabled={loading}>
                {loading ? 'Searching...' : 'Search Scenes'}
              </button>
              {error && <div style={{ color: '#f85149', fontSize: '12px', marginTop: '10px' }}>{error}</div>}

              {selectedScenes.length > 0 && (
                <div style={{ marginTop: '12px' }}>
                  <div style={{ fontSize: '11px', color: '#8b949e', marginBottom: '6px' }}>Selected: {selectedScenes.length}/2 scenes</div>
                  {selectedScenes.length === 2 && (
                    <button style={{ ...styles.button, background: '#1f6feb', marginBottom: '6px' }} onClick={handleDetectChange} disabled={loading}>
                      Detect Change
                    </button>
                  )}
                  {selectedScenes.length >= 1 && (
                    <button style={{ ...styles.button, background: '#8957e5' }} onClick={handleComputeIndices} disabled={processingIndex}>
                      {processingIndex ? 'Computing...' : 'Compute Indices'}
                    </button>
                  )}
                </div>
              )}

              <div style={{ marginTop: '12px' }}>
                <button style={{ ...styles.button, background: '#21262d', border: '1px solid #30363d' }} onClick={handleTimeSeries} disabled={loadingTimeSeries}>
                  {loadingTimeSeries ? 'Loading Time Series...' : 'Load Time Series'}
                </button>
              </div>
            </div>
          </div>

          <div style={styles.mapContainer}>
            {viewMode === '2d' ? (
              <div ref={mapRef} style={{ width: '100%', height: '100%', minHeight: '500px', borderRadius: '12px' }} />
            ) : (
              <div ref={globeRef} style={{ width: '100%', height: '100%', minHeight: '500px' }} />
            )}
          </div>

          <div>
            <div style={styles.panel}>
              <div style={styles.tabBar}>
                {(['scenes', 'indices', 'change', 'timeseries', 'provenance'] as ActivePanel[]).map(tab => (
                  <button key={tab} style={{ ...styles.tab, ...(activePanel === tab ? styles.tabActive : {}) }} onClick={() => setActivePanel(tab)}>
                    {tab === 'scenes' ? `Scenes (${searchResult?.scenes.length || 0})` : tab.charAt(0).toUpperCase() + tab.slice(1)}
                  </button>
                ))}
              </div>

              {activePanel === 'scenes' && (
                <div style={{ maxHeight: '500px', overflowY: 'auto' }}>
                  {!searchResult ? <div style={styles.placeholder}>Search for scenes</div>
                    : searchResult.scenes.length === 0 ? <div style={styles.placeholder}>No scenes found</div>
                    : searchResult.scenes.map(scene => (
                      <div key={scene.scene_id} style={{ ...styles.sceneCard, ...(selectedScenes.some(s => s.scene_id === scene.scene_id) ? styles.sceneCardSelected : {}) }} onClick={() => toggleSceneSelection(scene)}>
                        <div style={styles.sceneHeader}>
                          <span style={styles.sceneId}>{scene.scene_id.slice(0, 30)}</span>
                          <span style={{ ...styles.badge, background: scene.quality_grade === 'GOOD' ? '#3fb95020' : '#e3b34120', color: scene.quality_grade === 'GOOD' ? '#3fb950' : '#e3b341', border: `1px solid ${scene.quality_grade === 'GOOD' ? '#3fb95040' : '#e3b34140'}` }}>{scene.quality_grade}</span>
                        </div>
                        <div style={{ fontSize: '11px', color: '#8b949e' }}>{scene.dataset} · {new Date(scene.acquisition_time).toLocaleDateString()}</div>
                        <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '2px' }}>Cloud: {fmtCloud(scene.cloud_pct)} · {fmtRes(scene.resolution_m)} · {scene.bands.length} bands</div>
                      </div>
                    ))
                  }
                </div>
              )}

              {activePanel === 'indices' && (
                <div>
                  {indices.length === 0 ? <div style={styles.placeholder}>Select scenes and compute indices</div>
                    : indices.map((idx, i) => (
                      <div key={i} style={styles.indexResult}>
                        <div style={styles.indexHeader}>
                          <span style={styles.indexName}>{idx.name}</span>
                          <IntegrityBadge state={idx.integrity_state} />
                        </div>
                        <div style={styles.indexValue}>{idx.supported ? fmtVal(idx.mean) : 'UNSUPPORTED'}</div>
                        <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '4px' }}>
                          Formula: {idx.formula}<br />
                          Bands: {idx.source_bands.join(', ')}<br />
                          Valid pixels: {idx.valid_count.toLocaleString()} / {idx.total_count.toLocaleString()}<br />
                          {idx.uncertainty && <span style={{ color: '#f0883e' }}>⚠ {idx.uncertainty}</span>}
                        </div>
                      </div>
                    ))
                  }
                </div>
              )}

              {activePanel === 'change' && (
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
                      {changeResult.changed_area_km2 != null && (
                        <div style={{ fontSize: '12px', color: '#c9d1d9', marginTop: '8px' }}>
                          Changed area: {changeResult.changed_area_km2.toFixed(2)} km² ({changeResult.spatial_extent_pct?.toFixed(1)}%)
                        </div>
                      )}
                      {changeResult.uncertainty && (
                        <div style={{ fontSize: '11px', color: '#8b949e', marginTop: '8px', padding: '8px', background: 'rgba(1,4,9,0.4)', borderRadius: '6px' }}>
                          <strong>Uncertainty:</strong> {changeResult.uncertainty}
                        </div>
                      )}
                    </div>
                  ) : <div style={styles.placeholder}>Select 2 scenes and click Detect Change</div>}
                </div>
              )}

              {activePanel === 'timeseries' && (
                <div>
                  {timeSeries ? (
                    <div>
                      {timeSeries.statistics && (
                        <div style={styles.metricGrid}>
                          <div style={styles.metricCard}>
                            <div style={styles.metricValue}>{timeSeries.statistics.count}</div>
                            <div style={styles.metricLabel}>Observations</div>
                          </div>
                          <div style={styles.metricCard}>
                            <div style={styles.metricValue}>{fmtVal(timeSeries.statistics.mean)}</div>
                            <div style={styles.metricLabel}>Mean {timeSeries.index}</div>
                          </div>
                          <div style={styles.metricCard}>
                            <div style={styles.metricValue}>{fmtVal(timeSeries.statistics.min)}</div>
                            <div style={styles.metricLabel}>Min</div>
                          </div>
                          <div style={styles.metricCard}>
                            <div style={styles.metricValue}>{fmtVal(timeSeries.statistics.max)}</div>
                            <div style={styles.metricLabel}>Max</div>
                          </div>
                        </div>
                      )}
                      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
                        {timeSeries.observations.map((pt, i) => (
                          <div key={i} style={styles.timePoint}>
                            <span>{new Date(pt.date).toLocaleDateString()}</span>
                            <span style={{ color: '#26a69a', fontWeight: 600 }}>{pt.value.toFixed(4)}</span>
                            <span style={{ color: '#8b949e' }}>{(pt.confidence * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>
                      <div style={{ fontSize: '10px', color: '#8b949e', marginTop: '8px' }}>
                        {timeSeries.uncertainty}
                      </div>
                    </div>
                  ) : (
                    <div style={styles.placeholder}>
                      {loadingTimeSeries ? 'Loading...' : 'Click "Load Time Series" to fetch observations'}
                    </div>
                  )}
                </div>
              )}

              {activePanel === 'provenance' && (
                <div>
                  {selectedScenes.length > 0 ? selectedScenes.map(scene => (
                    <div key={scene.scene_id} style={{ ...styles.metricCard, marginBottom: '10px' }}>
                      <div style={{ fontSize: '12px', color: '#c9d1d9', lineHeight: 1.8 }}>
                        <div><strong>Provider:</strong> {scene.provider}</div>
                        <div><strong>Dataset:</strong> {scene.dataset}</div>
                        <div><strong>Scene:</strong> {scene.scene_id}</div>
                        <div><strong>Acquired:</strong> {new Date(scene.acquisition_time).toISOString()}</div>
                        <div><strong>Resolution:</strong> {fmtRes(scene.resolution_m)}</div>
                        <div><strong>Bands:</strong> {scene.bands.join(', ')}</div>
                        <div><strong>Cloud:</strong> {fmtCloud(scene.cloud_pct)}</div>
                      </div>
                    </div>
                  )) : <div style={styles.placeholder}>Select a scene to view provenance</div>}
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export { GeoExplorer };
