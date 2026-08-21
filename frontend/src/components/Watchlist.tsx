import React from 'react';
import { ASSETS } from '../types';

interface Props {
  selectedAsset: string;
  onSelect: (symbol: string) => void;
}

const CATEGORY_COLORS: Record<string, string> = {
  crypto: '#f0883e', commodity: '#e3b341', etf: '#58a6ff', equity_index: '#bc8cff', forex: '#3fb950',
};

export const Watchlist: React.FC<Props> = ({ selectedAsset, onSelect }) => {
  const watchlistData = ASSETS.map(a => ({
    ...a,
    lastPrice: (Math.random() * 1000 + 100).toFixed(2),
    change: ((Math.random() - 0.48) * 20).toFixed(2),
    changePct: ((Math.random() - 0.48) * 2).toFixed(2),
  }));

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Watchlist</span>
        <span style={styles.badge}>DEMO</span>
      </div>
      <div style={styles.list}>
        {watchlistData.map(item => {
          const isActive = item.symbol === selectedAsset;
          const isUp = parseFloat(item.changePct) >= 0;
          return (
            <div
              key={item.symbol}
              onClick={() => onSelect(item.symbol)}
              style={{
                ...styles.item,
                ...(isActive ? styles.itemActive : {}),
              }}
            >
              <div style={styles.itemTop}>
                <span style={{ ...styles.symbol, color: CATEGORY_COLORS[item.category] ?? '#f0f6fc' }}>
                  {item.symbol}
                </span>
                <span style={styles.price}>{item.lastPrice}</span>
              </div>
              <div style={styles.itemBottom}>
                <span style={styles.name}>{item.name}</span>
                <span style={{ color: isUp ? '#3fb950' : '#f85149' }}>
                  {isUp ? '+' : ''}{item.change} ({isUp ? '+' : ''}{item.changePct}%)
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { width: 240, background: '#0d1117', borderRight: '1px solid #21262d', display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', borderBottom: '1px solid #21262d' },
  title: { fontSize: 13, fontWeight: 600, color: '#f0f6fc' },
  badge: { fontSize: 9, background: '#f0883e', color: '#000', padding: '2px 6px', borderRadius: 4, fontWeight: 700 },
  list: { flex: 1, overflowY: 'auto' },
  item: { padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid #161b22', transition: 'background 0.15s' },
  itemActive: { background: '#1c2333' },
  itemTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  itemBottom: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 },
  symbol: { fontSize: 13, fontWeight: 700 },
  name: { fontSize: 11, color: '#8b949e' },
  price: { fontSize: 13, color: '#f0f6fc', fontWeight: 600 },
};
