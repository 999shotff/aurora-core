/**
 * AURORA Terminal — News & Research Panel.
 *
 * Fetches real news data from backend data fabric provider.
 * Shows DATA_UNAVAILABLE when no provider connected.
 * Never fabricates news headlines.
 */

import React, { useState, useEffect } from 'react';
import { GlassPanel } from '../shell/primitives';
import { Newspaper, FileText, Search, ExternalLink } from 'lucide-react';
import {
  getNewsStatus,
  searchNews,
  getResearchStatus,
  type NewsItem,
  type ProviderStatus,
} from '../../services/dataFabric';

const FRESHNESS_COLORS: Record<string, string> = {
  CURRENT: 'var(--aur-positive)',
  RECENT: 'var(--aur-accent)',
  HISTORICAL: 'var(--aur-ink-dim)',
  STALE: 'var(--aur-warning)',
  UNKNOWN: 'var(--aur-ink-faint)',
};

export const NewsResearchPanel: React.FC = () => {
  const [newsStatus, setNewsStatus] = useState<ProviderStatus | null>(null);
  const [researchStatus, setResearchStatus] = useState<ProviderStatus | null>(null);
  const [newsItems, setNewsItems] = useState<NewsItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    getNewsStatus().then(setNewsStatus).catch(() => {});
    getResearchStatus().then(setResearchStatus).catch(() => {});
  }, []);

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const result = await searchNews(searchQuery, 10);
      setNewsItems(result.items);
    } catch {
      setNewsItems([]);
    } finally {
      setLoading(false);
    }
  };

  const newsConnected = newsStatus?.state === 'READY';
  const researchConnected = researchStatus?.state === 'READY';

  return (
    <GlassPanel style={{ padding: '14px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Newspaper size={14} color="var(--aur-accent)" />
        <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--aur-ink-faint)', textTransform: 'uppercase' }}>
          News & Research
        </span>
      </div>

      {/* News section */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase' }}>
            News Feed
          </span>
          {newsStatus && (
            <span style={{
              fontSize: 9, fontWeight: 600, padding: '2px 6px', borderRadius: 4,
              background: newsConnected ? 'rgba(52,211,153,0.12)' : 'rgba(248,113,113,0.1)',
              color: newsConnected ? 'var(--aur-positive)' : 'var(--aur-negative)',
            }}>
              {newsConnected ? 'CONNECTED' : newsStatus.state}
            </span>
          )}
        </div>

        {!newsConnected ? (
          <div style={{
            padding: '10px 14px', background: 'rgba(248,113,113,0.08)',
            border: '1px solid rgba(248,113,113,0.2)', borderRadius: 8,
          }}>
            <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-negative)' }}>
              NEWS DATA UNAVAILABLE
            </div>
            <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)', marginTop: 2 }}>
              {newsStatus?.detail || 'No news provider connected'}
            </div>
          </div>
        ) : (
          <>
            {/* Search bar */}
            <div style={{ display: 'flex', gap: 6, marginBottom: 8 }}>
              <input
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                placeholder="Search news..."
                style={{
                  flex: 1, padding: '6px 10px', background: 'var(--aur-bg-elevated)',
                  border: '1px solid var(--aur-border)', borderRadius: 6,
                  color: 'var(--aur-ink)', fontSize: 11,
                }}
              />
              <button
                onClick={handleSearch}
                disabled={loading || !searchQuery.trim()}
                style={{
                  padding: '6px 10px', background: 'var(--aur-accent)', border: 'none',
                  borderRadius: 6, color: '#fff', fontSize: 11, cursor: 'pointer',
                  opacity: loading || !searchQuery.trim() ? 0.5 : 1,
                }}
              >
                <Search size={12} />
              </button>
            </div>

            {/* News items */}
            {newsItems.length > 0 ? (
              <div style={{ maxHeight: 300, overflowY: 'auto' }}>
                {newsItems.map(item => (
                  <div key={item.id} style={{
                    padding: '8px 10px', marginBottom: 4, background: 'var(--aur-bg-elevated)',
                    borderRadius: 6, borderLeft: `3px solid ${FRESHNESS_COLORS[item.freshness] || 'var(--aur-ink-faint)'}`,
                  }}>
                    <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-ink)', marginBottom: 2 }}>
                      {item.headline}
                    </div>
                    <div style={{ display: 'flex', gap: 8, fontSize: 9, color: 'var(--aur-ink-dim)' }}>
                      {item.publisher && <span>{item.publisher}</span>}
                      {item.published_at && <span>{new Date(item.published_at).toLocaleDateString()}</span>}
                      <span style={{ color: FRESHNESS_COLORS[item.freshness] }}>{item.freshness}</span>
                    </div>
                    {item.source_url && (
                      <a href={item.source_url} target="_blank" rel="noopener noreferrer"
                        style={{ fontSize: 9, color: 'var(--aur-accent)', display: 'flex', alignItems: 'center', gap: 3, marginTop: 2 }}>
                        <ExternalLink size={9} /> Source
                      </a>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div style={{ padding: '12px', textAlign: 'center', fontSize: 11, color: 'var(--aur-ink-dim)' }}>
                {loading ? 'Searching...' : 'Enter a query to search news'}
              </div>
            )}
          </>
        )}
      </div>

      {/* Research section */}
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
          <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--aur-ink-dim)', textTransform: 'uppercase' }}>
            Research Documents
          </span>
          {researchStatus && (
            <span style={{
              fontSize: 9, fontWeight: 600, padding: '2px 6px', borderRadius: 4,
              background: researchConnected ? 'rgba(52,211,153,0.12)' : 'rgba(248,113,113,0.1)',
              color: researchConnected ? 'var(--aur-positive)' : 'var(--aur-negative)',
            }}>
              {researchConnected ? 'CONNECTED' : researchStatus.state}
            </span>
          )}
        </div>
        <div style={{
          padding: '10px 14px', background: 'var(--aur-bg-elevated)',
          borderRadius: 8, border: '1px solid var(--aur-border-soft)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <FileText size={12} color="var(--aur-ink-dim)" />
            <span style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
              {researchConnected
                ? 'Research documents available'
                : researchStatus?.detail || 'No research provider connected'}
            </span>
          </div>
        </div>
      </div>
    </GlassPanel>
  );
};

export default NewsResearchPanel;
