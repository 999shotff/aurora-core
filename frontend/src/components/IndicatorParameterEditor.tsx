import React, { useState, useCallback } from 'react';
import { INDICATOR_GROUPS } from '../services/data';
import type { IndicatorDef, IndicatorParamDef } from '../services/data';

interface Props {
  indicatorParams: Record<string, Record<string, number>>;
  onUpdate: (indicatorId: string, paramId: string, value: number) => void;
  onReset: (indicatorId: string) => void;
}

export const IndicatorParameterEditor: React.FC<Props> = ({ indicatorParams, onUpdate, onReset }) => {
  const [expanded, setExpanded] = useState<string | null>(null);

  const toggleExpand = useCallback((id: string) => {
    setExpanded(prev => prev === id ? null : id);
  }, []);

  const configurable = INDICATOR_GROUPS.filter(g => g.params.length > 0);

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.title}>Parameters</span>
      </div>
      {configurable.map(ind => (
        <IndicatorParamRow
          key={ind.id}
          indicator={ind}
          isExpanded={expanded === ind.id}
          onToggle={() => toggleExpand(ind.id)}
          currentParams={indicatorParams[ind.id] ?? {}}
          onUpdate={(paramId, value) => onUpdate(ind.id, paramId, value)}
          onReset={() => onReset(ind.id)}
        />
      ))}
    </div>
  );
};

const IndicatorParamRow: React.FC<{
  indicator: IndicatorDef;
  isExpanded: boolean;
  onToggle: () => void;
  currentParams: Record<string, number>;
  onUpdate: (paramId: string, value: number) => void;
  onReset: () => void;
}> = ({ indicator, isExpanded, onToggle, currentParams, onUpdate, onReset }) => {
  const hasChanges = indicator.params.some(p => {
    const current = currentParams[p.id];
    return current !== undefined && current !== p.default;
  });

  return (
    <div style={styles.indicatorBlock}>
      <button style={styles.indicatorHeader} onClick={onToggle}>
        <span style={styles.indicatorName}>{indicator.name}</span>
        <span style={styles.expandIcon}>{isExpanded ? '\u25B2' : '\u25BC'}</span>
      </button>
      {isExpanded && (
        <div style={styles.paramList}>
          {indicator.params.map(param => (
            <ParamControl
              key={param.id}
              param={param}
              value={currentParams[param.id] ?? param.default}
              onChange={(v) => onUpdate(param.id, v)}
            />
          ))}
          <div style={styles.paramActions}>
            {hasChanges && (
              <button style={styles.resetBtn} onClick={onReset}>
                Reset
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const ParamControl: React.FC<{
  param: IndicatorParamDef;
  value: number;
  onChange: (value: number) => void;
}> = ({ param, value, onChange }) => {
  const [inputValue, setInputValue] = useState(String(value));
  const [isFocused, setIsFocused] = useState(false);

  const handleCommit = useCallback(() => {
    const parsed = parseFloat(inputValue);
    if (isNaN(parsed)) {
      setInputValue(String(value));
      return;
    }
    const clamped = Math.min(param.max, Math.max(param.min, parsed));
    const snapped = Math.round(clamped / param.step) * param.step;
    const final = Math.round(snapped * 1000) / 1000;
    setInputValue(String(final));
    if (final !== value) onChange(final);
    setIsFocused(false);
  }, [inputValue, value, param, onChange]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleCommit();
    if (e.key === 'Escape') {
      setInputValue(String(value));
      setIsFocused(false);
    }
  }, [handleCommit, value]);

  const handleSliderChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const v = parseFloat(e.target.value);
    setInputValue(String(v));
    onChange(v);
  }, [onChange]);

  return (
    <div style={styles.paramRow}>
      <label style={styles.paramLabel}>{param.label}</label>
      <div style={styles.paramControl}>
        <input
          type="range"
          min={param.min}
          max={param.max}
          step={param.step}
          value={value}
          onChange={handleSliderChange}
          style={styles.slider}
        />
        <input
          type="number"
          value={isFocused ? inputValue : String(value)}
          min={param.min}
          max={param.max}
          step={param.step}
          onFocus={() => { setIsFocused(true); setInputValue(String(value)); }}
          onBlur={handleCommit}
          onKeyDown={handleKeyDown}
          onChange={(e) => setInputValue(e.target.value)}
          style={styles.numberInput}
        />
      </div>
      <div style={styles.paramRange}>
        <span>{param.min}</span>
        <span>{param.max}</span>
      </div>
    </div>
  );
};

const styles: Record<string, React.CSSProperties> = {
  container: { borderTop: '1px solid #21262d' },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '6px 10px', borderBottom: '1px solid #161b22' },
  title: { fontSize: 10, fontWeight: 700, color: '#8b949e', textTransform: 'uppercase', letterSpacing: 0.5 },
  indicatorBlock: { borderBottom: '1px solid #161b22' },
  indicatorHeader: { display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', background: 'none', border: 'none', padding: '5px 10px', cursor: 'pointer', color: '#c9d1d9', fontSize: 11 },
  indicatorName: { fontWeight: 500 },
  expandIcon: { fontSize: 8, color: '#8b949e' },
  paramList: { padding: '4px 10px 8px' },
  paramRow: { marginBottom: 8 },
  paramLabel: { display: 'block', fontSize: 10, color: '#8b949e', marginBottom: 3 },
  paramControl: { display: 'flex', alignItems: 'center', gap: 6 },
  slider: { flex: 1, height: 3, appearance: 'none', background: '#21262d', borderRadius: 2, outline: 'none', cursor: 'pointer' },
  numberInput: { width: 52, background: '#161b22', border: '1px solid #21262d', borderRadius: 4, color: '#f0f6fc', fontSize: 11, padding: '2px 4px', textAlign: 'right', fontFamily: 'monospace', outline: 'none' },
  paramRange: { display: 'flex', justifyContent: 'space-between', fontSize: 9, color: '#484f58', marginTop: 2 },
  paramActions: { display: 'flex', justifyContent: 'flex-end', marginTop: 4 },
  resetBtn: { background: 'none', border: '1px solid #f0883e44', color: '#f0883e', padding: '2px 8px', borderRadius: 4, cursor: 'pointer', fontSize: 9, fontWeight: 600 },
};
