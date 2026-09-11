/**
 * AURORA Terminal — News & Research Panel.
 *
 * Unified research workspace. Shows NEWS DATA UNAVAILABLE when no provider connected.
 * Every source retains provenance: source, publisher, timestamp, URL, retrieval time, content hash, reliability.
 *
 * NO_DEPLOYMENT_SIGNAL. No fabricated news. No fake headlines.
 */

import React from 'react';
import { GlassPanel } from '../shell/primitives';
import { Newspaper, FileText, Search } from 'lucide-react';

export const NewsResearchPanel: React.FC = () => {
  return (
    <GlassPanel style={{ padding: '14px 18px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
        <Newspaper size={14} color="var(--aur-accent)" />
        <span
          style={{
            fontSize: 10,
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: 'var(--aur-ink-faint)',
            textTransform: 'uppercase',
          }}
        >
          News & Research
        </span>
      </div>

      {/* News section */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--aur-ink-dim)', marginBottom: 6, textTransform: 'uppercase' }}>
          News Feed
        </div>
        <div
          style={{
            padding: '10px 14px',
            background: 'rgba(248,113,113,0.08)',
            border: '1px solid rgba(248,113,113,0.2)',
            borderRadius: 8,
          }}
        >
          <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--aur-negative)' }}>
            NEWS DATA UNAVAILABLE
          </div>
          <div style={{ fontSize: 10, color: 'var(--aur-ink-dim)', marginTop: 2 }}>
            No news provider connected. Connect a news API to enable real-time intelligence.
          </div>
        </div>
      </div>

      {/* Research section */}
      <div style={{ marginBottom: 16 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--aur-ink-dim)', marginBottom: 6, textTransform: 'uppercase' }}>
          Research Documents
        </div>
        <div
          style={{
            padding: '10px 14px',
            background: 'var(--aur-bg-elevated)',
            borderRadius: 8,
            border: '1px solid var(--aur-border-soft)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
            <FileText size={12} color="var(--aur-ink-dim)" />
            <span style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>No research documents loaded</span>
          </div>
          <div style={{ fontSize: 10, color: 'var(--aur-ink-faint)' }}>
            Upload research PDFs or connect a document source to enable research intelligence.
          </div>
        </div>
      </div>

      {/* Evidence section */}
      <div>
        <div style={{ fontSize: 10, fontWeight: 600, color: 'var(--aur-ink-dim)', marginBottom: 6, textTransform: 'uppercase' }}>
          Evidence Sources
        </div>
        <div
          style={{
            padding: '10px 14px',
            background: 'var(--aur-bg-elevated)',
            borderRadius: 8,
            border: '1px solid var(--aur-border-soft)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Search size={12} color="var(--aur-ink-dim)" />
            <span style={{ fontSize: 11, color: 'var(--aur-ink-dim)' }}>
              Evidence graph is populated by reasoning queries
            </span>
          </div>
        </div>
      </div>
    </GlassPanel>
  );
};

export default NewsResearchPanel;
