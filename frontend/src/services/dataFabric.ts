/**
 * AURORA Data Fabric — Frontend Services.
 * All provider access occurs backend-side. No API keys exposed.
 */

import { API_BASE } from './config';

export interface ProviderStatus {
  provider: string;
  state: string;
  detail: string;
  last_success: string | null;
  error_count: number;
}

export interface NewsItem {
  id: string;
  headline: string;
  summary: string | null;
  publisher: string | null;
  source_url: string | null;
  published_at: string | null;
  freshness: string;
  reliability: string;
  provenance: string;
  asset_refs: string[];
}

export interface NewsSearchResult {
  query: string;
  count: number;
  items: NewsItem[];
}

export interface MacroObservation {
  value: number | null;
  date: string | null;
  freshness: string;
  status: string;
}

export interface MacroSeries {
  series_id: string;
  name: string;
  category: string;
  country: string;
  unit: string;
  frequency: string;
  source: string;
  latest_value: number | null;
  latest_date: string | null;
  observations?: MacroObservation[];
}

export interface MacroSearchResult {
  query: string;
  count: number;
  series: MacroSeries[];
}

export interface ResearchDocument {
  id: string;
  title: string;
  authors: string[];
  abstract: string | null;
  publisher: string | null;
  source_url: string | null;
  published_at: string | null;
  updated_at: string | null;
  categories: string[];
  freshness: string;
  reliability: string;
  provenance: string;
  content_hash: string | null;
  status: string;
}

export interface ResearchSearchResult {
  query: string;
  count: number;
  items: ResearchDocument[];
}

export interface DataFabricStatus {
  status: string;
  providers: Record<string, { name: string; state: string; detail: string }>;
}

// ── News API ──────────────────────────────────────────────────────────────

export async function getNewsStatus(): Promise<ProviderStatus> {
  const res = await fetch(`${API_BASE}/api/v1/news/status`);
  if (!res.ok) throw new Error(`News status failed: HTTP ${res.status}`);
  return res.json();
}

export async function searchNews(
  query: string,
  maxResults: number = 10
): Promise<NewsSearchResult> {
  const params = new URLSearchParams({ q: query, max_results: String(maxResults) });
  const res = await fetch(`${API_BASE}/api/v1/news/search?${params}`);
  if (!res.ok) throw new Error(`News search failed: HTTP ${res.status}`);
  return res.json();
}

// ── Macro API ─────────────────────────────────────────────────────────────

export async function getMacroStatus(): Promise<ProviderStatus> {
  const res = await fetch(`${API_BASE}/api/v1/macro/status`);
  if (!res.ok) throw new Error(`Macro status failed: HTTP ${res.status}`);
  return res.json();
}

export async function getMacroSeries(seriesId: string): Promise<MacroSeries> {
  const res = await fetch(`${API_BASE}/api/v1/macro/series/${encodeURIComponent(seriesId)}`);
  if (!res.ok) throw new Error(`Macro series failed: HTTP ${res.status}`);
  return res.json();
}

export async function searchMacro(
  query: string,
  maxResults: number = 10
): Promise<MacroSearchResult> {
  const params = new URLSearchParams({ q: query, max_results: String(maxResults) });
  const res = await fetch(`${API_BASE}/api/v1/macro/search?${params}`);
  if (!res.ok) throw new Error(`Macro search failed: HTTP ${res.status}`);
  return res.json();
}

// ── Research API ──────────────────────────────────────────────────────────

export async function getResearchStatus(): Promise<ProviderStatus> {
  const res = await fetch(`${API_BASE}/api/v1/research/status`);
  if (!res.ok) throw new Error(`Research status failed: HTTP ${res.status}`);
  return res.json();
}

export async function searchResearch(
  query: string,
  maxResults: number = 10
): Promise<ResearchSearchResult> {
  const params = new URLSearchParams({ q: query, max_results: String(maxResults) });
  const res = await fetch(`${API_BASE}/api/v1/research/search?${params}`);
  if (!res.ok) throw new Error(`Research search failed: HTTP ${res.status}`);
  return res.json();
}

// ── Data Fabric Overview ──────────────────────────────────────────────────

export async function getDataFabricStatus(): Promise<DataFabricStatus> {
  const res = await fetch(`${API_BASE}/api/v1/data/status`);
  if (!res.ok) throw new Error(`Data fabric status failed: HTTP ${res.status}`);
  return res.json();
}
