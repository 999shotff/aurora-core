import React, { useState, useEffect, useCallback, useMemo } from 'react';
import type { Asset, AssetCategory } from '../types';
import { ASSETS } from '../types';
import { API_BASE } from '../services/data';

interface Quote {
  symbol: string;
  price: number;
  change: number;
  changePct: number;
  high: number;
  low: number;
  open: number;
  volume: number;
}

type CategoryFilter = 'all' | AssetCategory;

const CATEGORY_LABELS: Record<CategoryFilter, string> = {
  all: 'All',
  crypto: 'Crypto',
  commodity: 'Commodities',
  equity_index: 'Indices',
  forex: 'Forex',
  etf: 'ETF',
};

const CATEGORY_COLORS: Record<string, string> = {
  crypto: '#f0883e',
  commodity: '#e3b341',
  etf: '#58a6ff',
  equity_index: '#bc8cff',
  forex: '#3fb950',
};

const MOCK_QUOTES: Record<string, number> = {
  'BTC-USD': 67432.18,
  'ETH-USD': 3521.47,
  GOLD: 2342.60,
  SILVER: 27.831,
  SPY: 532.14,
  QQQ: 461.28,
  NIFTY: 22147.00,
  NASDAQ: 16832.61,
  EURUSD: 1.08432,
  USDJPY: 154.823,
};

const MOCK_CHANGES: Record<string, { change: number; changePct: number }> = {
  'BTC-USD': { change: 1243.50, changePct: 1.88 },
  'ETH-USD': { change: -42.30, changePct: -1.19 },
  GOLD: { change: 18.40, changePct: 0.79 },
  SILVER: { change: -0.124, changePct: -0.44 },
  SPY: { change: 4.82, changePct: 0.91 },
  QQQ: { change: 8.15, changePct: 1.80 },
  NIFTY: { change: 186.30, changePct: 0.85 },
  NASDAQ: { change: 142.73, changePct: 0.86 },
  EURUSD: { change: 0.00234, changePct: 0.22 },
  USDJPY: { change: -0.342, changePct: -0.22 },
};

function loadFavorites(): string[] {
  try {
    const raw = localStorage.getItem('aurora_favorites');
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveFavorites(favs: string[]) {
  localStorage.setItem('aurora_favorites', JSON.stringify(favs));
}

const AssetExplorer: React.FC<{ onSelectAsset: (symbol: string) => void }> = ({ onSelectAsset }) => {
  const [search, setSearch] = useState('');
  const [category, setCategory] = useState<CategoryFilter>('all');
  const [favorites, setFavorites] = useState<string[]>(loadFavorites);
  const [quotes, setQuotes] = useState<Record<string, Quote>>({});
  const [loading, setLoading] = useState<Record<string, boolean>>({});
  const [showFavsOnly, setShowFavsOnly] = useState(false);

  const filteredAssets = useMemo(() => {
    let list = ASSETS;
    if (category !== 'all') {
      list = list.filter(a => a.category === category);
    }
    if (showFavsOnly) {
      list = list.filter(a => favorites.includes(a.symbol));
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter(
        a =>
          a.symbol.toLowerCase().includes(q) ||
          a.name.toLowerCase().includes(q) ||
          a.description.toLowerCase().includes(q)
      );
    }
    return list;
  }, [category, search, favorites, showFavsOnly]);

  const fetchQuote = useCallback(async (symbol: string) => {
    setLoading(prev => ({ ...prev, [symbol]: true }));
    try {
      const res = await fetch(`${API_BASE}/market/${symbol}/quote`);
      if (!res.ok) throw new Error('not ok');
      const data: Quote = await res.json();
      setQuotes(prev => ({ ...prev, [symbol]: data }));
    } catch {
      const mockPrice = MOCK_QUOTES[symbol] ?? 0;
      const mockChange = MOCK_CHANGES[symbol] ?? { change: 0, changePct: 0 };
      setQuotes(prev => ({
        ...prev,
        [symbol]: {
          symbol,
          price: mockPrice,
          change: mockChange.change,
          changePct: mockChange.changePct,
          high: mockPrice * 1.012,
          low: mockPrice * 0.988,
          open: mockPrice - mockChange.change,
          volume: 0,
        },
      }));
    } finally {
      setLoading(prev => ({ ...prev, [symbol]: false }));
    }
  }, []);

  useEffect(() => {
    filteredAssets.forEach(a => fetchQuote(a.symbol));
  }, [filteredAssets, fetchQuote]);

  const toggleFav = (symbol: string) => {
    setFavorites(prev => {
      const next = prev.includes(symbol) ? prev.filter(s => s !== symbol) : [...prev, symbol];
      saveFavorites(next);
      return next;
    });
  };

  const formatPrice = (asset: Asset, price: number) => {
    if (asset.category === 'forex') return price.toFixed(5);
    if (asset.category === 'crypto') return price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    return price.toFixed(asset.decimals);
  };

  return (
    <div style={styles.page}>
      <header style={styles.header}>
        <div style={styles.headerInner}>
          <h1 style={styles.logo}>
            AURORA <span style={styles.logoAccent}>CORE</span>
          </h1>
          <span style={styles.headerTag}>Asset Explorer</span>
        </div>
      </header>

      <main style={styles.main}>
        <div style={styles.toolbar}>
          <div style={styles.searchWrapper}>
            <svg style={styles.searchIcon} width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#8b949e" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="11" cy="11" r="8" />
              <line x1="21" y1="21" x2="16.65" y2="16.65" />
            </svg>
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search assets by symbol, name, or description..."
              style={styles.searchInput}
            />
          </div>
          <div style={styles.filterRow}>
            <div style={styles.categoryButtons}>
              {(Object.keys(CATEGORY_LABELS) as CategoryFilter[]).map(cat => (
                <button
                  key={cat}
                  onClick={() => setCategory(cat)}
                  style={{
                    ...styles.filterBtn,
                    ...(category === cat ? styles.filterBtnActive : {}),
                  }}
                >
                  {CATEGORY_LABELS[cat]}
                </button>
              ))}
            </div>
            <button
              onClick={() => setShowFavsOnly(p => !p)}
              style={{
                ...styles.favFilterBtn,
                ...(showFavsOnly ? styles.favFilterBtnActive : {}),
              }}
            >
              ★ Favorites {showFavsOnly ? `(${favorites.length})` : ''}
            </button>
          </div>
        </div>

        <div style={styles.grid}>
          {filteredAssets.map(asset => {
            const q = quotes[asset.symbol];
            const isFav = favorites.includes(asset.symbol);
            const isUp = q ? q.changePct >= 0 : true;
            const catColor = CATEGORY_COLORS[asset.category] ?? '#8b949e';

            return (
              <div
                key={asset.symbol}
                style={styles.card}
                onClick={() => onSelectAsset(asset.symbol)}
              >
                <div style={styles.cardHeader}>
                  <div style={styles.cardTitleBlock}>
                    <span style={{ ...styles.symbol, color: catColor }}>{asset.symbol}</span>
                    <span style={styles.name}>{asset.name}</span>
                  </div>
                  <button
                    onClick={e => { e.stopPropagation(); toggleFav(asset.symbol); }}
                    style={styles.favBtn}
                    title={isFav ? 'Remove from favorites' : 'Add to favorites'}
                  >
                    {isFav ? '★' : '☆'}
                  </button>
                </div>

                <div style={styles.priceBlock}>
                  {q ? (
                    <>
                      <span style={styles.price}>{formatPrice(asset, q.price)}</span>
                      <span style={{ ...styles.change, color: isUp ? '#3fb950' : '#f85149' }}>
                        {isUp ? '+' : ''}{q.change.toFixed(2)} ({isUp ? '+' : ''}{q.changePct.toFixed(2)}%)
                      </span>
                    </>
                  ) : loading[asset.symbol] ? (
                    <span style={styles.loading}>Loading...</span>
                  ) : (
                    <span style={styles.loading}>--</span>
                  )}
                </div>

                <div style={styles.cardMeta}>
                  <span style={{ ...styles.categoryBadge, background: `${catColor}18`, color: catColor, border: `1px solid ${catColor}40` }}>
                    {CATEGORY_LABELS[asset.category] ?? asset.category}
                  </span>
                  <span style={styles.exchange}>{asset.exchange}</span>
                </div>

                <p style={styles.description}>{asset.description}</p>
              </div>
            );
          })}

          {filteredAssets.length === 0 && (
            <div style={styles.empty}>
              <span style={styles.emptyIcon}>∅</span>
              <p style={styles.emptyText}>No assets match your search.</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  page: {
    minHeight: '100vh',
    background: '#010409',
    color: '#c9d1d9',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
  },
  header: {
    position: 'sticky',
    top: 0,
    zIndex: 50,
    background: 'rgba(1, 4, 9, 0.85)',
    backdropFilter: 'blur(12px)',
    borderBottom: '1px solid #21262d',
    padding: '16px 0',
  },
  headerInner: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '0 32px',
    display: 'flex',
    alignItems: 'center',
    gap: '24px',
  },
  logo: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#e6edf3',
    letterSpacing: '2px',
    margin: 0,
    textTransform: 'uppercase',
  },
  logoAccent: { color: '#26a69a' },
  headerTag: {
    fontSize: '13px',
    color: '#8b949e',
    padding: '4px 12px',
    border: '1px solid #21262d',
    borderRadius: '6px',
  },
  main: {
    maxWidth: '1400px',
    margin: '0 auto',
    padding: '32px',
  },
  toolbar: { marginBottom: '32px' },
  searchWrapper: {
    position: 'relative',
    marginBottom: '16px',
  },
  searchIcon: {
    position: 'absolute',
    left: '14px',
    top: '50%',
    transform: 'translateY(-50%)',
    pointerEvents: 'none',
  },
  searchInput: {
    width: '100%',
    padding: '14px 16px 14px 42px',
    background: 'rgba(13, 17, 23, 0.7)',
    backdropFilter: 'blur(8px)',
    border: '1px solid #21262d',
    borderRadius: '10px',
    color: '#e6edf3',
    fontSize: '15px',
    outline: 'none',
    transition: 'border-color 0.2s',
    boxSizing: 'border-box',
  },
  filterRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    flexWrap: 'wrap',
  },
  categoryButtons: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  filterBtn: {
    padding: '8px 18px',
    borderRadius: '8px',
    border: '1px solid #21262d',
    background: 'rgba(13, 17, 23, 0.5)',
    color: '#8b949e',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  filterBtnActive: {
    background: 'rgba(38, 166, 154, 0.15)',
    color: '#26a69a',
    border: '1px solid rgba(38, 166, 154, 0.4)',
  },
  favFilterBtn: {
    padding: '8px 18px',
    borderRadius: '8px',
    border: '1px solid #21262d',
    background: 'rgba(13, 17, 23, 0.5)',
    color: '#8b949e',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
    marginLeft: 'auto',
  },
  favFilterBtnActive: {
    background: 'rgba(227, 179, 65, 0.15)',
    color: '#e3b341',
    border: '1px solid rgba(227, 179, 65, 0.4)',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
    gap: '20px',
  },
  card: {
    background: 'rgba(13, 17, 23, 0.6)',
    backdropFilter: 'blur(8px)',
    border: '1px solid #21262d',
    borderRadius: '14px',
    padding: '24px',
    cursor: 'pointer',
    transition: 'border-color 0.2s, transform 0.15s, box-shadow 0.2s',
    display: 'flex',
    flexDirection: 'column',
    gap: '14px',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
  },
  cardTitleBlock: {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px',
  },
  symbol: {
    fontSize: '18px',
    fontWeight: 700,
    letterSpacing: '0.5px',
  },
  name: {
    fontSize: '13px',
    color: '#8b949e',
  },
  favBtn: {
    background: 'none',
    border: 'none',
    fontSize: '20px',
    color: '#e3b341',
    cursor: 'pointer',
    padding: '0 4px',
    lineHeight: 1,
  },
  priceBlock: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '12px',
    flexWrap: 'wrap',
  },
  price: {
    fontSize: '26px',
    fontWeight: 700,
    color: '#f0f6fc',
    fontFamily: 'monospace',
  },
  change: {
    fontSize: '13px',
    fontWeight: 600,
  },
  loading: {
    fontSize: '14px',
    color: '#6e7681',
  },
  cardMeta: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
  },
  categoryBadge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '3px 10px',
    borderRadius: '6px',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
  },
  exchange: {
    fontSize: '12px',
    color: '#6e7681',
  },
  description: {
    fontSize: '13px',
    color: '#6e7681',
    lineHeight: '1.5',
    margin: 0,
  },
  empty: {
    gridColumn: '1 / -1',
    textAlign: 'center',
    padding: '80px 24px',
  },
  emptyIcon: {
    fontSize: '48px',
    color: '#21262d',
    display: 'block',
    marginBottom: '16px',
  },
  emptyText: {
    color: '#8b949e',
    fontSize: '16px',
  },
};

export { AssetExplorer };
