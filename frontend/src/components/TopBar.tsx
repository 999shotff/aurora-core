import React from 'react';
import { Asset, Timeframe, TIMEFRAMES, ASSETS } from '../types';

interface Props {
  selectedAsset: string;
  selectedTimeframe: Timeframe;
  onAssetChange: (symbol: string) => void;
  onTimeframeChange: (tf: Timeframe) => void;
}

export const TopBar: React.FC<Props> = ({ selectedAsset, selectedTimeframe, onAssetChange, onTimeframeChange }) => {
  const currentAsset = ASSETS.find(a => a.symbol === selectedAsset);
  return (
    <div style={styles.topBar}>
      <div style={styles.logo}>
        <span style={styles.logoIcon}>◆</span>
        <span style={styles.logoText}>AURORA CORE</span>
        <span style={styles.logoSub}>Trading Terminal</span>
      </div>
      <div style={styles.controls}>
        <select
          value={selectedAsset}
          onChange={e => onAssetChange(e.target.value)}
          style={styles.select}
        >
          {ASSETS.map(a => (
            <option key={a.symbol} value={a.symbol}>{a.symbol} — {a.name}</option>
          ))}
        </select>
        <div style={styles.timeframes}>
          {TIMEFRAMES.map(tf => (
            <button
              key={tf}
              onClick={() => onTimeframeChange(tf)}
              style={{
                ...styles.tfButton,
                ...(tf === selectedTimeframe ? styles.tfButtonActive : {}),
              }}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      <div style={styles.status}>
        <span style={styles.statusDot} />
        <span style={styles.statusText}>DEMO DATA</span>
        {currentAsset && <span style={styles.exchange}>{currentAsset.exchange}</span>}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  topBar: {
    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
    padding: '8px 16px', background: '#0d1117', borderBottom: '1px solid #21262d',
    height: 56, gap: 16,
  },
  logo: { display: 'flex', alignItems: 'center', gap: 8 },
  logoIcon: { fontSize: 20, color: '#58a6ff' },
  logoText: { fontSize: 16, fontWeight: 700, color: '#f0f6fc', letterSpacing: 1 },
  logoSub: { fontSize: 11, color: '#8b949e', marginLeft: 4 },
  controls: { display: 'flex', alignItems: 'center', gap: 12 },
  select: {
    background: '#161b22', color: '#f0f6fc', border: '1px solid #30363d',
    borderRadius: 6, padding: '6px 12px', fontSize: 13, cursor: 'pointer',
  },
  timeframes: { display: 'flex', gap: 2 },
  tfButton: {
    background: 'transparent', color: '#8b949e', border: '1px solid transparent',
    borderRadius: 4, padding: '4px 8px', fontSize: 12, cursor: 'pointer',
  },
  tfButtonActive: { background: '#1f6feb', color: '#ffffff', borderColor: '#1f6feb' },
  status: { display: 'flex', alignItems: 'center', gap: 8 },
  statusDot: { width: 8, height: 8, borderRadius: '50%', background: '#f0883e' },
  statusText: { fontSize: 11, color: '#f0883e', fontWeight: 600 },
  exchange: { fontSize: 11, color: '#8b949e', marginLeft: 8 },
};
