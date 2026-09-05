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
  crypto: 'var(--aur-accent-2)',
  commodity: 'var(--aur-warning)',
  etf: 'var(--aur-accent)',
  equity_index: 'var(--aur-stage-analysis)',
  forex: 'var(--aur-positive)',
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
    <div className="watchlist">
      <div className="watchlist-header">
        <span className="watchlist-title">Watchlist</span>
        <span className={`watchlist-status ${overallDemo ? 'watchlist-status-demo' : overallStale ? 'watchlist-status-stale' : 'watchlist-status-live'}`}>
          {overallDemo ? 'DEMO' : overallStale ? 'STALE' : 'LIVE'}
        </span>
      </div>
      <div className="watchlist-list">
        {ASSETS.map(item => {
          const q = quotes[item.symbol];
          const price = q?.lastPrice;
          const isActive = item.symbol === selectedAsset;
          const isDemo = q?.isDemo ?? true;
          const stale = q?.stale ?? false;
          const provider = q?.provider ?? '\u2014';
          return (
            <button
              key={item.symbol}
              className={`watchlist-item ${isActive ? 'watchlist-item-active' : ''}`}
              onClick={() => onSelect(item.symbol)}
            >
              <div className="watchlist-item-top">
                <span className="watchlist-symbol" style={{ color: CATEGORY_COLORS[item.category] ?? 'var(--aur-ink)' }}>
                  {item.symbol}
                </span>
                <span className="watchlist-price">{price !== null && price !== undefined ? price.toFixed(item.decimals) : '\u2014'}</span>
              </div>
              <div className="watchlist-item-bottom">
                <span className="watchlist-name">{item.name}</span>
                <span className={`watchlist-source ${isDemo ? 'watchlist-source-demo' : stale ? 'watchlist-source-stale' : 'watchlist-source-live'}`}>
                  {isDemo ? 'DEMO' : stale ? 'STALE' : provider}
                </span>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
};
