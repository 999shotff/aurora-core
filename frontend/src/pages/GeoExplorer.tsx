import React, { useState, useCallback, useEffect, useRef } from 'react';
import { API_BASE } from '../services/config';
import { fetchAssets, fetchMultiSourceObservations } from '../services/geoAssets';
import { AssetLayerControl } from '../components/geo/AssetLayerControl';
import { buildAssetInspectorBody } from '../components/geo/AssetInspector';

/* eslint-disable @typescript-eslint/no-explicit-any */
interface LeafletLib {
  map: (el: HTMLElement, opts: Record<string, unknown>) => any;
  tileLayer: (url: string, opts: Record<string, unknown>) => any;
  rectangle: (bounds: number[][], opts: Record<string, unknown>) => any;
  marker: (latlng: number[], opts?: Record<string, unknown>) => any;
  popup: () => any;
  icon: (opts: Record<string, unknown>) => any;
  control: { layers: (base: Record<string, unknown>, overlays: Record<string, unknown>, opts?: Record<string, unknown>) => any };
}
interface WindowWithLibs {
  L?: LeafletLib;
  Cesium?: any;
  _auroraGlobeReady?: boolean;
  _auroraGlobeCleanup?: (() => void) | null;
  THREE?: any;
}
const win = window as unknown as WindowWithLibs;
/* eslint-enable @typescript-eslint/no-explicit-any */
import { ObservationTimeline } from '../components/geo/ObservationTimeline';
import { GeoEvidencePanel } from '../components/geo/GeoEvidencePanel';
import type { GeoAsset, GeoAssetObservation, AssetCategorySummary, AssetType } from '../types/geoAssets';

type IntegrityState = 'DATA_AVAILABLE' | 'DATA_STALE' | 'DATA_UNAVAILABLE' | 'LOW_CONFIDENCE' | 'INSUFFICIENT_RESOLUTION' | 'INSUFFICIENT_TEMPORAL_COVERAGE' | 'PROCESSING_FAILED' | 'PROVIDER_ERROR' | 'AUTH_REQUIRED' | 'NO_CHANGE';
type ViewMode = '2d' | '3d' | 'eo';
type ActivePanel = 'scenes' | 'indices' | 'change' | 'timeseries' | 'provenance' | 'assets' | 'evidence';

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
  value: number | null;
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

const PRESET_AOIS: Record<string, { south: number; west: number; north: number; east: number }> = {
  'Port of Los Angeles': { south: 33.72, west: -118.35, north: 33.80, east: -118.20 },
  'Sahel Region': { south: 12.0, west: -5.0, north: 16.0, east: 5.0 },
  'Great Barrier Reef': { south: -18.5, east: 147.5, north: -14.5, west: 146.5 },
  'Nile Delta': { south: 29.5, east: 32.5, north: 31.5, west: 29.5 },
  'Amazon Basin': { south: -5.0, west: -65.0, north: 0.0, east: -55.0 },
  'Custom': { south: 0, west: 0, north: 1, east: 1 },
};

function fmtCloud(pct: number): string { return pct.toFixed(1) + '%'; }
function fmtRes(m: number): string { return m < 1 ? (m * 1000).toFixed(0) + 'm' : m.toFixed(0) + 'm'; }
function fmtVal(v: number): string { return isNaN(v) ? 'N/A' : v.toFixed(4); }

function IntegrityBadge({ state }: { state: IntegrityState }) {
  const colors: Record<string, string> = {
    DATA_AVAILABLE: '#34D399', DATA_STALE: '#FBBF24', DATA_UNAVAILABLE: '#F87171',
    LOW_CONFIDENCE: '#FF8A65', INSUFFICIENT_RESOLUTION: '#FF8A65',
    INSUFFICIENT_TEMPORAL_COVERAGE: '#FF8A65', PROCESSING_FAILED: '#F87171',
    PROVIDER_ERROR: '#F87171', AUTH_REQUIRED: '#FBBF24', NO_CHANGE: '#34D399',
  };
  const c = colors[state] || '#9096A8';
  return (
    <span className="geo-badge" style={{ background: `${c}20`, color: c, border: `1px solid ${c}40` }}>
      {state.replace(/_/g, ' ')}
    </span>
  );
}

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

  // M32 multi-source state
  const [assets, setAssets] = useState<GeoAsset[]>([]);
  const [assetSummaries, setAssetSummaries] = useState<AssetCategorySummary[]>([]);
  const [enabledLayers, setEnabledLayers] = useState<Set<AssetType>>(new Set(['satellite']));
  const [selectedAsset] = useState<GeoAsset | null>(null);
  const [observations, setObservations] = useState<GeoAssetObservation[]>([]);

  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<unknown>(null);
  const globeRef = useRef<HTMLDivElement>(null);
  const cameraRef = useRef<{ lat: number; lng: number; zoom: number }>({ lat: 0, lng: 0, zoom: 8 });

  // Fetch M32 assets on mount
  useEffect(() => {
    const ac = new AbortController();
    fetchAssets(undefined, ac.signal).then(r => { setAssets(r.assets); setAssetSummaries(r.categorySummaries); });
    fetchMultiSourceObservations(undefined, ac.signal).then(setObservations);
    return () => ac.abort();
  }, []);

  // Leaflet map init
  useEffect(() => {
    if (viewMode !== '2d' || !mapRef.current || mapInstanceRef.current) return;

    const L = win.L;
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

    function initMap() {
      const L = win.L;
      if (!L || !mapRef.current || mapInstanceRef.current) return;
      const centerLat = (parseFloat(south) + parseFloat(north)) / 2;
      const centerLng = (parseFloat(west) + parseFloat(east)) / 2;
      const map = L.map(mapRef.current, {
        center: [centerLat, centerLng],
        zoom: 8,
        zoomControl: false,
        attributionControl: false,
      });

      const basemapProvider = import.meta.env.VITE_BASEMAP_PROVIDER || 'osm';
      const cartoKey = import.meta.env.VITE_CARTO_API_KEY || '';

      let tileUrl: string;
      let tileAttribution: string;
      let tileSubdomains: string | string[];

      if (basemapProvider === 'carto' && cartoKey) {
        tileUrl = `https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png?api_key=${cartoKey}`;
        tileAttribution = '&copy; CARTO &copy; OpenStreetMap';
        tileSubdomains = 'abcd';
      } else {
        tileUrl = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
        tileAttribution = '&copy; OpenStreetMap';
        tileSubdomains = 'abc';
      }

      L.tileLayer(tileUrl, {
        maxZoom: 19,
        subdomains: tileSubdomains,
        attribution: tileAttribution,
      }).addTo(map);

      const bounds = [
        [parseFloat(south), parseFloat(west)],
        [parseFloat(north), parseFloat(east)],
      ];
      const rect = (L as { rectangle: (bounds: number[][], opts: Record<string, unknown>) => { addTo: (m: unknown) => unknown; on: (evt: string, cb: () => void) => unknown } }).rectangle(bounds, {
        color: '#7C9EFF',
        weight: 2,
        fillOpacity: 0.15,
        draggable: true,
      }).addTo(map);

      (rect as any).on('dblclick', () => {
        const b = (rect as any).getBounds();
        const sw = b.getSouthWest();
        const ne = b.getNorthEast();
        const coords = sw();
        const coords2 = ne();
        setSouth(coords.lat.toFixed(2));
        setWest(coords.lng.toFixed(2));
        setNorth(coords2.lat.toFixed(2));
        setEast(coords2.lng.toFixed(2));
      });

      (map as any).on('moveend', () => {
        const center = (map as any).getCenter();
        const zoom = (map as any).getZoom();
        cameraRef.current = { lat: center.lat, lng: center.lng, zoom: zoom };
      });

      mapInstanceRef.current = map;
    }

    return () => {
      if (mapInstanceRef.current) {
        const map = mapInstanceRef.current as any;
        if (typeof map.remove === 'function') map.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [viewMode, south, west, north, east]);

  // Globe init (Three.js fallback for 3D)
  useEffect(() => {
    if (viewMode !== '3d' || !globeRef.current || win._auroraGlobeReady) return;

    const container = globeRef.current;
    const script = document.createElement('script');
    script.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
    script.onload = () => {
      setTimeout(() => {
        if (win._auroraGlobeReady || !container) return;
        const w = container.clientWidth;
        const h = container.clientHeight;
        const THREE = win.THREE as any;
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0x000011);
        const camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 1000);
        camera.position.z = 2.5;
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(w, h);
        renderer.setPixelRatio(window.devicePixelRatio);
        container.appendChild(renderer.domElement);

        const earthGeo = new THREE.SphereGeometry(1, 64, 64);
        const earthMat = new THREE.MeshPhongMaterial({ color: 0x224488, emissive: 0x112244, specular: 0x444444, shininess: 25 });
        const loader = new THREE.TextureLoader();
        loader.load('https://eoimages.gsfc.nasa.gov/images/imagerecords/57000/57747/land_ocean_ice_2048.jpg', (texture: Record<string, unknown>) => {
          earthMat.map = texture;
          earthMat.needsUpdate = true;
        });
        const earth = new THREE.Mesh(earthGeo, earthMat);
        scene.add(earth);
        const wireGeo = new THREE.SphereGeometry(1.001, 32, 32);
        const wireMat = new THREE.MeshBasicMaterial({ color: 0x7C9EFF, wireframe: true, transparent: true, opacity: 0.08 });
        const wire = new THREE.Mesh(wireGeo, wireMat);
        scene.add(wire);
        scene.add(new THREE.AmbientLight(0x404040, 0.6));
        const dirLight = new THREE.DirectionalLight(0xffffff, 0.8);
        dirLight.position.set(5, 3, 5);
        scene.add(dirLight);

        let dragging = false;
        let prevMouse = { x: 0, y: 0 };
        const canvas = renderer.domElement as HTMLElement;
        canvas.addEventListener('mousedown', (e: MouseEvent) => { dragging = true; prevMouse = { x: e.clientX, y: e.clientY }; });
        canvas.addEventListener('mousemove', (e: MouseEvent) => {
          if (!dragging) return;
          earth.rotation.y += (e.clientX - prevMouse.x) * 0.005;
          earth.rotation.x += (e.clientY - prevMouse.y) * 0.005;
          wire.rotation.y = earth.rotation.y;
          wire.rotation.x = earth.rotation.x;
          prevMouse = { x: e.clientX, y: e.clientY };
        });
        canvas.addEventListener('mouseup', () => { dragging = false; });
        canvas.addEventListener('mouseleave', () => { dragging = false; });
        canvas.addEventListener('wheel', (e: WheelEvent) => {
          e.preventDefault();
          camera.position.z = Math.max(1.1, Math.min(10, camera.position.z + e.deltaY * 0.001));
        }, { passive: false });

        let touchStart: { x: number; y: number } | null = null;
        canvas.addEventListener('touchstart', (e: TouchEvent) => {
          if (e.touches.length === 1) touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        });
        canvas.addEventListener('touchmove', (e: TouchEvent) => {
          if (!touchStart || e.touches.length !== 1) return;
          e.preventDefault();
          earth.rotation.y += (e.touches[0].clientX - touchStart.x) * 0.005;
          earth.rotation.x += (e.touches[0].clientY - touchStart.y) * 0.005;
          wire.rotation.y = earth.rotation.y;
          wire.rotation.x = earth.rotation.x;
          touchStart = { x: e.touches[0].clientX, y: e.touches[0].clientY };
        }, { passive: false });
        canvas.addEventListener('touchend', () => { touchStart = null; });

        win._auroraGlobeReady = true;
        let animId = 0;
        const animate = () => { animId = requestAnimationFrame(animate); renderer.render(scene, camera); };
        animate();

        win._auroraGlobeCleanup = () => {
          cancelAnimationFrame(animId);
          renderer.dispose();
          if (container.contains(renderer.domElement)) container.removeChild(renderer.domElement);
        };
      }, 100);
    };
    document.head.appendChild(script);

    return () => {
      const cleanup = win._auroraGlobeCleanup;
      if (typeof cleanup === 'function') {
        cleanup();
        win._auroraGlobeCleanup = null;
        win._auroraGlobeReady = false;
      }
    };
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
          const resp = await fetch(`${API_BASE}/api/v1/geo/index`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              provider: scene.provider, dataset: scene.dataset,
              aoi_name: searchResult.aoi.name,
              south: searchResult.aoi.south, west: searchResult.aoi.west,
              north: searchResult.aoi.north, east: searchResult.aoi.east,
              date: scene.acquisition_time, index: idx,
            }),
          });
          if (resp.ok) {
            const data = await resp.json();
            results.push({
              name: idx, supported: data.supported || false,
              mean: data.statistics?.mean ?? NaN, std: data.statistics?.std ?? NaN,
              min_val: data.statistics?.min ?? NaN, max_val: data.statistics?.max ?? NaN,
              valid_count: data.statistics?.count ?? 0, total_count: data.statistics?.total_pixels ?? 0,
              formula: data.formula || '', source_bands: data.source_bands || [],
              uncertainty: data.uncertainty || data.error || '',
              integrity_state: data.integrity_state || 'DATA_UNAVAILABLE',
            });
          } else {
            results.push({
              name: idx, supported: false,
              mean: NaN, std: NaN, min_val: NaN, max_val: NaN,
              valid_count: 0, total_count: 0,
              formula: '', source_bands: [],
              uncertainty: `API error: HTTP ${resp.status}`,
              integrity_state: 'PROVIDER_ERROR',
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
        before_values: {}, after_values: {},
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
        index: 'NDVI', cloud_threshold: maxCloud,
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

  const handleToggleLayer = (type: AssetType) => {
    setEnabledLayers(prev => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type); else next.add(type);
      return next;
    });
  };

  return (
    <div className="aur-geo-wrap">
      <div className="geo-layout">
        {/* Mode Selector Bar */}
        <div className="geo-mode-bar">
          {(['2d', '3d', 'eo'] as ViewMode[]).map(mode => (
            <button
              key={mode}
              className={`geo-mode-btn ${viewMode === mode ? 'geo-mode-btn-active' : ''}`}
              onClick={() => setViewMode(mode)}
            >
              {mode === '2d' ? '2D Map' : mode === '3d' ? '3D Globe' : 'Earth Obs'}
            </button>
          ))}
        </div>

        {/* Visualization Body */}
        <div className="geo-body">
          {/* Map / Globe Area */}
          <div className="geo-map-area">
            {viewMode === '2d' && <div ref={mapRef} />}
            {(viewMode === '3d' || viewMode === 'eo') && <div ref={globeRef} />}
          </div>

          {/* Floating Left Panel — AOI + Search Controls */}
          <div className="geo-float-left">
            <div className="aur-glass aur-glass--md aur-glass--radial geo-float-panel" style={{ maxHeight: 'calc(100vh - 180px)' }}>
              <div className="geo-float-panel-header">
                <span className="geo-float-panel-title">Area of Interest</span>
                <span style={{ fontSize: 10, color: 'var(--aur-ink-faint)' }}>{aoiName}</span>
              </div>
              <div className="geo-float-panel-body">
                <div className="geo-metric-grid">
                  <div className="geo-metric-card">
                    <div className="geo-metric-value">{calcArea().toFixed(0)}</div>
                    <div className="geo-metric-label">Area km²</div>
                  </div>
                  <div className="geo-metric-card">
                    <div className="geo-metric-value" style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                      ({parseFloat(south).toFixed(2)}°, {parseFloat(west).toFixed(2)}°)
                    </div>
                    <div className="geo-metric-label">SW Corner</div>
                  </div>
                </div>

                <div className="geo-field">
                  <label className="geo-label">Presets</label>
                  <div className="geo-preset-wrap">
                    {Object.keys(PRESET_AOIS).map(name => (
                      <button key={name} className="geo-btn geo-btn-secondary geo-btn-sm" onClick={() => handlePreset(name)}>{name}</button>
                    ))}
                  </div>
                </div>

                <div className="geo-coord-row">
                  <div className="geo-field"><label className="geo-label">South</label><input className="geo-input" type="number" step="0.01" value={south} onChange={e => setSouth(e.target.value)} /></div>
                  <div className="geo-field"><label className="geo-label">West</label><input className="geo-input" type="number" step="0.01" value={west} onChange={e => setWest(e.target.value)} /></div>
                </div>
                <div className="geo-coord-row">
                  <div className="geo-field"><label className="geo-label">North</label><input className="geo-input" type="number" step="0.01" value={north} onChange={e => setNorth(e.target.value)} /></div>
                  <div className="geo-field"><label className="geo-label">East</label><input className="geo-input" type="number" step="0.01" value={east} onChange={e => setEast(e.target.value)} /></div>
                </div>

                <hr className="geo-separator" />

                <div className="geo-field">
                  <label className="geo-label">Date Range</label>
                  <div className="geo-coord-row">
                    <input className="geo-input" type="date" value={startDate} onChange={e => setStartDate(e.target.value)} />
                    <input className="geo-input" type="date" value={endDate} onChange={e => setEndDate(e.target.value)} />
                  </div>
                </div>

                <div className="geo-field">
                  <label className="geo-label">Max Cloud ({maxCloud}%)</label>
                  <input style={{ width: '100%', accentColor: 'var(--aur-accent)' }} type="range" min="0" max="100" step="5" value={maxCloud} onChange={e => setMaxCloud(Number(e.target.value))} />
                </div>

                <div className="geo-field">
                  <label className="geo-label">Provider</label>
                  <select className="geo-select" value={provider} onChange={e => setProvider(e.target.value)}>
                    <option value="">All</option>
                    <option value="copernicus_sentinel">Copernicus Sentinel</option>
                    <option value="nasa_gibs">NASA GIBS</option>
                    <option value="skyfi">SkyFi</option>
                  </select>
                </div>

                <div className="geo-field">
                  <label className="geo-label">Dataset</label>
                  <select className="geo-select" value={dataset} onChange={e => setDataset(e.target.value)}>
                    <option value="">Auto</option>
                    <option value="S2L2A">Sentinel-2 L2A</option>
                    <option value="S2L1C">Sentinel-2 L1C</option>
                    <option value="S1GRD">Sentinel-1 GRD</option>
                  </select>
                </div>

                <button className="geo-btn" onClick={handleSearch} disabled={loading}>
                  {loading ? 'Searching...' : 'Search Scenes'}
                </button>
                {error && <div style={{ color: 'var(--aur-negative)', fontSize: 11, marginTop: 8 }}>{error}</div>}

                {selectedScenes.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', marginBottom: 6 }}>Selected: {selectedScenes.length}/2 scenes</div>
                    {selectedScenes.length === 2 && (
                      <button className="geo-btn geo-btn-blue" style={{ marginBottom: 4 }} onClick={handleDetectChange} disabled={loading}>
                        Detect Change
                      </button>
                    )}
                    {selectedScenes.length >= 1 && (
                      <button className="geo-btn geo-btn-purple" onClick={handleComputeIndices} disabled={processingIndex}>
                        {processingIndex ? 'Computing...' : 'Compute Indices'}
                      </button>
                    )}
                  </div>
                )}

                <button className="geo-btn geo-btn-secondary" style={{ marginTop: 8 }} onClick={handleTimeSeries} disabled={loadingTimeSeries}>
                  {loadingTimeSeries ? 'Loading...' : 'Load Time Series'}
                </button>
              </div>
            </div>
          </div>

          {/* Floating Right Panel — Asset Layers + Inspector */}
          <div className="geo-float-right">
            <div className="aur-glass aur-glass--md aur-glass--radial geo-float-panel" style={{ maxHeight: 'calc(100vh - 180px)' }}>
              <div className="geo-float-panel-header">
                <span className="geo-float-panel-title">Data Sources</span>
              </div>
              <div className="geo-float-panel-body">
                <AssetLayerControl summaries={assetSummaries} enabled={enabledLayers} onToggle={handleToggleLayer} />
                {selectedAsset && (
                  <div style={{ marginTop: 10 }}>
                    {buildAssetInspectorBody(selectedAsset)}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Disclaimer */}
          <div className="geo-disclaimer">
            <strong style={{ color: 'var(--aur-accent-2)' }}>EXPERIMENTAL</strong> — Research Evidence Only. Satellite observations are NOT predictions. No targeting.
          </div>
        </div>

        {/* Bottom Tabs */}
        <div className="geo-bottom-tabs">
          <div className="geo-tab-bar">
            {(['scenes', 'indices', 'change', 'timeseries', 'provenance', 'assets', 'evidence'] as ActivePanel[]).map(tab => (
              <button key={tab} className={`geo-tab ${activePanel === tab ? 'geo-tab-active' : ''}`} onClick={() => setActivePanel(tab)}>
                {tab === 'scenes' ? `Scenes (${searchResult?.scenes.length || 0})`
                  : tab === 'assets' ? `Assets (${assets.length})`
                  : tab === 'evidence' ? `Evidence (${observations.length})`
                  : tab.charAt(0).toUpperCase() + tab.slice(1)}
              </button>
            ))}
            <div className="geo-tab-spacer" />
          </div>

          <div className="geo-tab-content">
            {/* Scenes Tab */}
            {activePanel === 'scenes' && (
              <div style={{ height: '100%', overflowY: 'auto', padding: '6px 8px' }}>
                {!searchResult
                  ? <div className="geo-placeholder">Search for scenes</div>
                  : searchResult.scenes.length === 0
                    ? <div className="geo-placeholder">No scenes found</div>
                    : searchResult.scenes.map(scene => (
                      <div key={scene.scene_id} className={`geo-scene-card ${selectedScenes.some(s => s.scene_id === scene.scene_id) ? 'geo-scene-card-selected' : ''}`} onClick={() => toggleSceneSelection(scene)}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 3 }}>
                          <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-accent)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', maxWidth: 200 }}>{scene.scene_id.slice(0, 30)}</span>
                          <IntegrityBadge state={scene.quality_grade === 'GOOD' ? 'DATA_AVAILABLE' : 'DATA_STALE'} />
                        </div>
                        <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)' }}>{scene.dataset} · {new Date(scene.acquisition_time).toLocaleDateString()}</div>
                        <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', marginTop: 1 }}>Cloud: {fmtCloud(scene.cloud_pct)} · {fmtRes(scene.resolution_m)} · {scene.bands.length} bands</div>
                      </div>
                    ))
                }
              </div>
            )}

            {/* Indices Tab */}
            {activePanel === 'indices' && (
              <div style={{ height: '100%', overflowY: 'auto', padding: '6px 8px' }}>
                {indices.length === 0
                  ? <div className="geo-placeholder">Select scenes and compute indices</div>
                  : indices.map((idx, i) => (
                    <div key={i} className="geo-scene-card" style={{ cursor: 'default' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                        <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--aur-accent)' }}>{idx.name}</span>
                        <IntegrityBadge state={idx.integrity_state} />
                      </div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: 'var(--aur-ink)', fontFamily: "'Space Grotesk', monospace" }}>
                        {idx.supported ? fmtVal(idx.mean) : idx.integrity_state}
                      </div>
                      <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', marginTop: 4 }}>
                        {idx.formula && <>Formula: {idx.formula}<br /></>}
                        {idx.source_bands.length > 0 && <>Bands: {idx.source_bands.join(', ')}<br /></>}
                        {idx.valid_count > 0 && <>Valid pixels: {idx.valid_count.toLocaleString()} / {idx.total_count.toLocaleString()}<br /></>}
                        {idx.integrity_state === 'DATA_UNAVAILABLE' && (
                          <span style={{ color: 'var(--aur-accent-2)' }}>Required spectral bands unavailable from selected source. GIBS provides RGB visualization imagery only.</span>
                        )}
                        {idx.integrity_state === 'AUTH_REQUIRED' && (
                          <span style={{ color: 'var(--aur-accent-2)' }}>Authentication required for this provider.</span>
                        )}
                        {idx.uncertainty && idx.integrity_state !== 'DATA_UNAVAILABLE' && (
                          <span style={{ color: 'var(--aur-accent-2)' }}>{idx.uncertainty}</span>
                        )}
                      </div>
                    </div>
                  ))
                }
              </div>
            )}

            {/* Change Tab */}
            {activePanel === 'change' && (
              <div style={{ height: '100%', overflowY: 'auto', padding: '6px 8px' }}>
                {changeResult ? (
                  <div>
                    <div className="geo-metric-grid">
                      <div className="geo-metric-card">
                        <div className="geo-metric-value" style={{ color: changeResult.change_detected ? 'var(--aur-accent-2)' : 'var(--aur-positive)', fontSize: 13 }}>
                          {changeResult.change_detected ? 'CHANGE DETECTED' : 'NO CHANGE'}
                        </div>
                        <div className="geo-metric-label">Result</div>
                      </div>
                      <div className="geo-metric-card">
                        <div className="geo-metric-value">{changeResult.confidence != null ? (changeResult.confidence * 100).toFixed(0) + '%' : 'N/A'}</div>
                        <div className="geo-metric-label">Confidence</div>
                      </div>
                    </div>
                    <IntegrityBadge state={changeResult.integrity_state} />
                    {changeResult.changed_area_km2 != null && (
                      <div style={{ fontSize: 11, color: 'var(--aur-ink-dim)', marginTop: 8 }}>
                        Changed area: {changeResult.changed_area_km2.toFixed(2)} km² ({changeResult.spatial_extent_pct?.toFixed(1)}%)
                      </div>
                    )}
                    {changeResult.uncertainty && (
                      <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)', marginTop: 8, padding: 8, background: 'var(--aur-glass)', borderRadius: 6 }}>
                        <strong>Uncertainty:</strong> {changeResult.uncertainty}
                      </div>
                    )}
                  </div>
                ) : <div className="geo-placeholder">Select 2 scenes and click Detect Change</div>}
              </div>
            )}

            {/* Time Series Tab */}
            {activePanel === 'timeseries' && (
              <div style={{ height: '100%', overflowY: 'auto', padding: '6px 8px' }}>
                {timeSeries ? (
                  <div>
                    {timeSeries.statistics && Object.keys(timeSeries.statistics).length > 0 && (
                      <div className="geo-metric-grid">
                        <div className="geo-metric-card">
                          <div className="geo-metric-value">{timeSeries.statistics.count}</div>
                          <div className="geo-metric-label">Observations</div>
                        </div>
                        <div className="geo-metric-card">
                          <div className="geo-metric-value">{fmtVal(timeSeries.statistics.mean)}</div>
                          <div className="geo-metric-label">Mean {timeSeries.index}</div>
                        </div>
                        <div className="geo-metric-card">
                          <div className="geo-metric-value">{fmtVal(timeSeries.statistics.min)}</div>
                          <div className="geo-metric-label">Min</div>
                        </div>
                        <div className="geo-metric-card">
                          <div className="geo-metric-value">{fmtVal(timeSeries.statistics.max)}</div>
                          <div className="geo-metric-label">Max</div>
                        </div>
                      </div>
                    )}
                    {!timeSeries.statistics || Object.keys(timeSeries.statistics).length === 0 ? (
                      <div style={{ padding: 10, background: 'rgba(240, 138, 62, 0.08)', borderRadius: 6, fontSize: 11, color: 'var(--aur-accent-2)' }}>
                        No valid index values in time series. GIBS provides RGB visualization imagery only. Scientific spectral indices require NIR/SWIR bands.
                      </div>
                    ) : null}
                    <div style={{ maxHeight: 200, overflowY: 'auto' }}>
                      {timeSeries.observations.map((pt, i) => (
                        <div key={i} className="geo-time-point">
                          <span>{new Date(pt.date).toLocaleDateString()}</span>
                          <span style={{ color: pt.value != null ? 'var(--aur-accent)' : 'var(--aur-accent-2)', fontWeight: 600 }}>
                            {pt.value != null ? (pt.value as number).toFixed(4) : 'DATA_UNAVAILABLE'}
                          </span>
                          <span style={{ color: 'var(--aur-ink-faint)', fontSize: 9 }}>{pt.integrity_state || 'UNKNOWN'}</span>
                        </div>
                      ))}
                    </div>
                    <div style={{ fontSize: 9, color: 'var(--aur-ink-faint)', marginTop: 6 }}>{timeSeries.uncertainty}</div>
                  </div>
                ) : (
                  <div className="geo-placeholder">
                    {loadingTimeSeries ? 'Loading...' : 'Click "Load Time Series" to fetch observations'}
                  </div>
                )}
              </div>
            )}

            {/* Provenance Tab */}
            {activePanel === 'provenance' && (
              <div style={{ height: '100%', overflowY: 'auto', padding: '6px 8px' }}>
                {selectedScenes.length > 0 ? selectedScenes.map(scene => (
                  <div key={scene.scene_id} className="geo-scene-card" style={{ cursor: 'default' }}>
                    <div style={{ fontSize: 11, color: 'var(--aur-ink)', lineHeight: 1.8 }}>
                      <div><strong>Provider:</strong> {scene.provider}</div>
                      <div><strong>Dataset:</strong> {scene.dataset}</div>
                      <div><strong>Scene:</strong> {scene.scene_id}</div>
                      <div><strong>Acquired:</strong> {new Date(scene.acquisition_time).toISOString()}</div>
                      <div><strong>Resolution:</strong> {fmtRes(scene.resolution_m)}</div>
                      <div><strong>Bands:</strong> {scene.bands.join(', ')}</div>
                      <div><strong>Cloud:</strong> {fmtCloud(scene.cloud_pct)}</div>
                    </div>
                  </div>
                )) : <div className="geo-placeholder">Select a scene to view provenance</div>}
              </div>
            )}

            {/* M32 Assets Tab */}
            {activePanel === 'assets' && (
              <div style={{ height: '100%', overflowY: 'auto', padding: '6px 8px' }}>
                <ObservationTimeline observations={observations} />
              </div>
            )}

            {/* M32 Evidence Tab */}
            {activePanel === 'evidence' && (
              <div style={{ height: '100%', overflowY: 'auto', padding: '6px 8px' }}>
                <GeoEvidencePanel observations={observations} title="Multi-source evidence" />
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export { GeoExplorer };
