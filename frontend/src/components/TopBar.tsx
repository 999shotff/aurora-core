import React from 'react';
import type { Timeframe } from '../types';
import { TIMEFRAMES, ASSETS } from '../types';

interface Props {
  selectedAsset: string;
  selectedTimeframe: Timeframe;
  onAssetChange: (symbol: string) => void;
  onTimeframeChange: (tf: Timeframe) => void;
  isDemo?: boolean;
  stale?: boolean;
  provider?: string;
}

export const TopBar: React.FC<Props> = ({ selectedAsset, selectedTimeframe, onAssetChange, onTimeframeChange, isDemo, stale, provider }) => {
  const currentAsset = ASSETS.find(a => a.symbol === selectedAsset);
  const statusColor = isDemo ? 'var(--aur-accent-2)' : stale ? 'var(--aur-warning)' : 'var(--aur-positive)';
  const statusText = isDemo ? 'DEMO DATA' : stale ? 'STALE DATA' : 'LIVE DATA';
  return (
    <div className="market-topbar">
      <div className="market-topbar-logo">
        <span className="market-topbar-icon">&#9670;</span>
        <span className="market-topbar-name">AURORA CORE</span>
        <span className="market-topbar-sub">Market Terminal</span>
      </div>
      <div className="market-topbar-controls">
        <select
          value={selectedAsset}
          onChange={e => onAssetChange(e.target.value)}
          className="market-topbar-select"
        >
          {ASSETS.map(a => (
            <option key={a.symbol} value={a.symbol}>{a.symbol} &mdash; {a.name}</option>
          ))}
        </select>
        <div className="market-topbar-tfs">
          {TIMEFRAMES.map(tf => (
            <button
              key={tf}
              onClick={() => onTimeframeChange(tf)}
              className={`market-topbar-tf ${tf === selectedTimeframe ? 'market-topbar-tf-active' : ''}`}
            >
              {tf}
            </button>
          ))}
        </div>
      </div>
      <div className="market-topbar-status">
        <span className="market-topbar-dot" style={{ background: statusColor }} />
        <span className="market-topbar-status-text" style={{ color: statusColor }}>{statusText}</span>
        {provider && <span className="market-topbar-provider">{provider}</span>}
        {currentAsset && <span className="market-topbar-exchange">{currentAsset.exchange}</span>}
      </div>
    </div>
  );
};
