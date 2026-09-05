import { API_BASE } from './config';
import type { AssetListResponse, AssetType, GeoAssetObservation } from '../types/geoAssets';

const UNAVAILABLE_SUMMARY = (assetType: AssetType) => ({
  assetType,
  connected: false,
  assetCount: 0,
  observationCount: 0,
  note: 'DATA SOURCE NOT CONNECTED',
});

const ALL_TYPES: AssetType[] = ['satellite', 'balloon', 'uav', 'ground_sensor', 'subsurface'];

/**
 * Fetches the real asset list from the backend. If the backend is
 * unreachable (network error, non-2xx), this does NOT fabricate data —
 * it returns an honest all-UNAVAILABLE response so the UI can say so.
 */
export async function fetchAssets(type?: AssetType, signal?: AbortSignal): Promise<AssetListResponse> {
  try {
    const params = type ? `?type=${encodeURIComponent(type)}` : '';
    const res = await fetch(`${API_BASE}/api/v1/geo/assets${params}`, { signal });
    if (!res.ok) throw new Error(`Backend returned ${res.status}`);
    return (await res.json()) as AssetListResponse;
  } catch {
    return {
      assets: [],
      count: 0,
      categorySummaries: ALL_TYPES.map(UNAVAILABLE_SUMMARY),
    };
  }
}

export async function fetchMultiSourceObservations(type?: AssetType, signal?: AbortSignal): Promise<GeoAssetObservation[]> {
  try {
    const params = type ? `?type=${encodeURIComponent(type)}` : '';
    const res = await fetch(`${API_BASE}/api/v1/geo/observations/multi-source${params}`, { signal });
    if (!res.ok) throw new Error(`Backend returned ${res.status}`);
    const data = await res.json();
    return data.observations as GeoAssetObservation[];
  } catch {
    return [];
  }
}
