export type AssetType = 'satellite' | 'balloon' | 'uav' | 'ground_sensor' | 'subsurface';

export type AssetAvailability = 'LIVE' | 'DERIVED' | 'REGISTERED' | 'DEMO' | 'STALE' | 'UNAVAILABLE';

export interface AssetLocation {
  latitude: number | null;
  longitude: number | null;
  altitudeM: number | null;
  depthM: number | null;
}

export interface GeoAsset {
  assetId: string;
  assetType: AssetType;
  name: string;
  source: string;
  availability: AssetAvailability;
  status: string;
  capabilities: string[];
  metadata: Record<string, string>;
  location: AssetLocation;
  lastObservationAt: string | null;
  evidenceRefs: string[];
  limitations: string[];
}

export interface GeoAssetObservation {
  observationId: string;
  assetId: string;
  assetType: AssetType;
  observationType: string;
  timestamp: string;
  availability: AssetAvailability;
  source: string;
  value: number | string | null;
  unit: string;
  confidence: number;
  limitations: string[];
  evidenceRefs: string[];
}

export interface AssetCategorySummary {
  assetType: AssetType;
  connected: boolean;
  assetCount: number;
  observationCount: number;
  note: string;
}

export interface AssetListResponse {
  assets: GeoAsset[];
  count: number;
  categorySummaries: AssetCategorySummary[];
}

export const ASSET_TYPE_LABEL: Record<AssetType, string> = {
  satellite: 'Satellites',
  balloon: 'Balloons',
  uav: 'UAVs',
  ground_sensor: 'Ground Sensors',
  subsurface: 'Subsurface Assets',
};
