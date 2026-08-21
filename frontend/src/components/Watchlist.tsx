import React, { useState, useEffect, useCallback } from 'react';
import { ASSETS } from '../types';
import { fetchQuoteFromBackend } from '../services/data';

interface Props {
  selectedAsset: string;
  onSelect: (symbol: string) => void;
}

interface QuoteData {
  symbol: string;
  name: string;
  lastPrice: number | null;
  provider: string;
  isDemo: boolean;
  stale: boolean;
}

const CATEGORY_COLORS: Record<string, string> = {
  crypto: '#f0883e', commodity: '#e3b341', etf: '#58a6ff', equity_index: '#bc8cff', forex: '#3fb950',
};

export const Watchlist: React.FC<Props> = ({ selectedAsset, onSelect }) => {
  const [quotes, setQuotes] = useState<Record<string, QuoteData>>({});

  const loadQuotes = useCallback(async () => {
    const results: Record<string, QuoteData> = {};
    await Promise.all(
      ASSETS.map(async (a) => {
        try {
          const resp = await fetchQuoteFromBackend(a.symbol);
          if (resp) {
            results[a.symbol] = {
              symbol: a.symbol,
              name: a.name,
              lastPrice: resp.last_price,
              provider: resp.provider,
              isDemo: resp.is_demo,
              stale: resp.source_status === 'stale',
            };
          } else {
            results[a.symbol] = { symbol: a.symbol, name: a.name, lastPrice: null, provider: 'unavailable', isDemo: true, stale: false };
          }
        } catch {
          results[a.symbol] = { symbol: a.symbol, name: a.name, lastPrice: null, provider: 'unavailable', isDemo: true, stale: false };
        }
      })
    );
    setQuotes(results);
  }, []);

  useEffect(() => {
    loadQuotes();
    const interval = setInterval(loadQuotes, 60000);
    return () => clearInterval(interval);
  }, [loadQuotes]);

  const overallDemo = Object.values(quotes).every(q => q.isDemo || q.lastPrice === null);
  const overallStale = Object.values(quotes).some(q => q.stale);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Watchlist</span>
        <span style={{
          ...styles.badge,
          background: overallDemo ? '#f0883e' : overallStale ? '#d29922' : '#26a69a',
        }}>
          {overallDemo ? 'DEMO' : overallStale ? 'STALE' : 'LIVE'}
        </span>
      </div>
      <div style={styles.list}>
        {ASSETS.map(item => {
          const q = quotes[item.symbol];
          const price = q?.lastPrice;
          const isActive = item.symbol === selectedAsset;
          const provider = q?.provider ?? '—';
          const isDemo = q?.isDemo ?? true;
          const stale = q?.stale ?? false;
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
                <span style={styles.price}>{price !== null && price !== undefined ? price.toFixed(item.decimals) : '—'}</span>
              </div>
              <div style={styles.itemBottom}>
                <span style={styles.name}>{item.name}</span>
                <span style={{
                  fontSize: 9, fontWeight: 700, padding: '1px 4px', borderRadius: 3,
                  background: isDemo ? '#f0883e22' : stale ? '#d2992222' : '#26a69a22',
                  color: isDemo ? '#f0883e' : stale ? '#d29922' : '#26a69a',
                }}>
                  {isDemo ? 'DEMO' : stale ? 'STALE' : provider}
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
  container: { width: 240, minWidth: 200, background: '#0d1117', borderRight: '1px solid #21262d', display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 12px', borderBottom: '1px solid #21262d' },
  title: { fontSize: 13, fontWeight: 600, color: '#f0f6fc' },
  badge: { fontSize: 9, color: '#000', padding: '2px 6px', borderRadius: 4, fontWeight: 700 },
  list: { flex: 1, overflowY: 'auto' },
  item: { padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid #161b22', transition: 'background 0.15s' },
  itemActive: { background: '#1c2333' },
  itemTop: { display: 'flex', justifyContent: 'space-between', alignItems: 'center' },
  itemBottom: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 4 },
  symbol: { fontSize: 13, fontWeight: 700 },
  name: { fontSize: 11, color: '#8b949e' },
  price: { fontSize: 13, color: '#f0f6fc', fontWeight: 600, fontFamily: 'monospace' },
};
