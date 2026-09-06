import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { Settings, RotateCcw, Check, X, AlertTriangle, Database, Clock } from 'lucide-react';
import { GlassPanel, StatusBadge, LoadingState } from '../components/shell/primitives';
import { INDICATOR_GROUPS, computeAllIndicators, fetchOHLCV } from '../services/data';
import type { OHLCBar, IndicatorSeries, Timeframe } from '../types';
import {
  loadIndicatorSettings,
  saveIndicatorSettings,
  resetIndicatorSettings,
  getEnabledSet,
  getParamsRecord,
  validateIndicatorParams,
  extractLatestValues,
  type IndicatorSettingsState,
  type IndicatorFullState,
} from '../lib/indicatorSettings';
import { useEventBus } from '../lib/eventBus';

const DEBOUNCE_MS = 300;

export const IndicatorsPage: React.FC = () => {
  const { emit } = useEventBus();
  const [settings, setSettings] = useState<IndicatorSettingsState>(loadIndicatorSettings);
  const [bars, setBars] = useState<OHLCBar[]>([]);
  const [series, setSeries] = useState<IndicatorSeries[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAsset] = useState('BTC-USD');
  const [selectedTimeframe] = useState<Timeframe>('1D');
  const [lastSaved, setLastSaved] = useState<boolean | null>(null);
  const [editingIndicator, setEditingIndicator] = useState<string | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      try {
        const result = await fetchOHLCV(selectedAsset, selectedTimeframe, 200);
        if (!mounted) return;
        if (!result.empty) {
          setBars(result.bars);
          const enabled = getEnabledSet(settings);
          const params = getParamsRecord(settings);
          setSeries(computeAllIndicators(result.bars, enabled, params));
        }
      } catch {
        if (mounted) setBars([]);
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => { mounted = false; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (bars.length === 0) return;
    const enabled = getEnabledSet(settings);
    const params = getParamsRecord(settings);
    setSeries(computeAllIndicators(bars, enabled, params));
    setSettings(prev => ({ ...prev, lastCalculated: Date.now() }));
  }, [bars, settings.indicators]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      const ok = saveIndicatorSettings(settings);
      setLastSaved(ok);
      setTimeout(() => setLastSaved(null), 2000);
    }, DEBOUNCE_MS);
    return () => { if (debounceRef.current) clearTimeout(debounceRef.current); };
  }, [settings]);

  const handleToggle = useCallback((id: string) => {
    setSettings(prev => ({
      ...prev,
      indicators: prev.indicators.map(ind =>
        ind.id === id ? { ...ind, enabled: !ind.enabled } : ind
      ),
    }));
    emit('indicator_toggle', `${id.toUpperCase()} toggled`, 'live');
  }, [emit]);

  const handleParamChange = useCallback((indicatorId: string, paramId: string, value: number) => {
    setSettings(prev => ({
      ...prev,
      indicators: prev.indicators.map(ind =>
        ind.id === indicatorId ? { ...ind, params: { ...ind.params, [paramId]: value } } : ind
      ),
    }));
  }, []);

  const handleReset = useCallback(() => {
    const defaults = resetIndicatorSettings();
    setSettings(defaults);
    emit('indicator_toggle', 'All indicators reset to defaults', 'live');
  }, [emit]);

  const handleResetSingle = useCallback((indicatorId: string) => {
    const def = INDICATOR_GROUPS.find(d => d.id === indicatorId);
    if (!def) return;
    const defaultParams = Object.fromEntries(def.params.map(p => [p.id, p.default]));
    setSettings(prev => ({
      ...prev,
      indicators: prev.indicators.map(ind =>
        ind.id === indicatorId ? { ...ind, params: defaultParams } : ind
      ),
    }));
  }, []);

  const indicatorStates: IndicatorFullState[] = useMemo(() => {
    return settings.indicators.map(ind => {
      const def = INDICATOR_GROUPS.find(d => d.id === ind.id);
      if (!def) return null;

      const validation = validateIndicatorParams(ind.id, ind.params);
      const hasEnoughData = bars.length >= def.minDataLength;
      const values = ind.enabled && hasEnoughData
        ? extractLatestValues(series, ind.id, def.subSeries)
        : [];

      let status: IndicatorFullState['status'] = 'ok';
      if (!ind.enabled) status = 'ok';
      else if (!hasEnoughData) status = 'insufficient_data';
      else if (values.length === 0 || values.every(v => v.value === null)) status = 'unavailable';
      else if (!validation.valid) status = 'unavailable';

      return {
        id: ind.id,
        name: def.name,
        group: def.group,
        enabled: ind.enabled,
        overlay: def.overlay,
        minDataLength: def.minDataLength,
        params: ind.params,
        paramDefs: def.params,
        values,
        subSeries: def.subSeries,
        status,
      };
    }).filter((s): s is IndicatorFullState => s !== null);
  }, [settings, series, bars]);

  const grouped = useMemo(() => {
    const groups: Record<string, IndicatorFullState[]> = {
      TREND: [], MOMENTUM: [], VOLATILITY: [], VOLUME: [], LEVELS: [],
    };
    for (const ind of indicatorStates) {
      if (groups[ind.group]) groups[ind.group].push(ind);
    }
    return groups;
  }, [indicatorStates]);

  const activeCount = settings.indicators.filter(i => i.enabled).length;
  const totalCount = settings.indicators.length;

  return (
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <Settings size={16} color="var(--aur-accent)" />
            <h1 style={{ fontSize: '18px', fontWeight: 600, fontFamily: 'var(--aur-font-display)', margin: 0 }}>
              INDICATORS
            </h1>
          </div>
          <p style={{ fontSize: '12px', color: 'var(--aur-ink-dim)', margin: 0 }}>
            Indicator values & configuration
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {lastSaved !== null && (
            <span style={{ fontSize: '11px', color: lastSaved ? 'var(--aur-positive)' : 'var(--aur-negative)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              {lastSaved ? <Check size={12} /> : <X size={12} />}
              {lastSaved ? 'Saved' : 'Error'}
            </span>
          )}
          <button
            onClick={handleReset}
            className="aur-btn"
            style={{ fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
            aria-label="Reset all indicator settings to defaults"
          >
            <RotateCcw size={12} />
            RESET ALL
          </button>
        </div>
      </div>

      {/* Overview */}
      <GlassPanel style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', gap: '24px' }}>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--aur-ink-dim)', marginBottom: '2px' }}>ACTIVE</div>
              <div style={{ fontSize: '20px', fontWeight: 600, fontFamily: 'var(--aur-font-display)', color: 'var(--aur-accent)' }}>
                {activeCount}
              </div>
            </div>
            <div>
              <div style={{ fontSize: '11px', color: 'var(--aur-ink-dim)', marginBottom: '2px' }}>AVAILABLE</div>
              <div style={{ fontSize: '20px', fontWeight: 600, fontFamily: 'var(--aur-font-display)' }}>
                {totalCount}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={12} color="var(--aur-ink-dim)" />
            <span style={{ fontSize: '11px', color: 'var(--aur-ink-dim)' }}>
              {settings.lastCalculated
                ? `Last calculation: ${new Date(settings.lastCalculated).toLocaleTimeString()}`
                : 'Not yet calculated'}
            </span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Database size={12} color="var(--aur-ink-dim)" />
            <span style={{ fontSize: '11px', color: 'var(--aur-ink-dim)' }}>
              {selectedAsset} · {selectedTimeframe}
            </span>
            <StatusBadge origin={bars.length > 0 ? 'live' : 'demo'} small />
          </div>
        </div>
      </GlassPanel>

      {loading && (
        <GlassPanel>
          <LoadingState label="Loading market data for indicator computation..." />
        </GlassPanel>
      )}

      {!loading && bars.length === 0 && (
        <GlassPanel>
          <div style={{ textAlign: 'center', padding: '24px' }}>
            <AlertTriangle size={24} color="var(--aur-warning)" style={{ marginBottom: '8px' }} />
            <div style={{ fontSize: '14px', fontWeight: 500, marginBottom: '4px' }}>NO MARKET DATA</div>
            <div style={{ fontSize: '12px', color: 'var(--aur-ink-dim)' }}>
              Open Market Observatory to load a dataset, then return here.
            </div>
          </div>
        </GlassPanel>
      )}

      {!loading && bars.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          {(['TREND', 'MOMENTUM', 'VOLATILITY', 'VOLUME', 'LEVELS'] as const).map(group => {
            const items = grouped[group];
            if (!items || items.length === 0) return null;
            return (
              <GlassPanel key={group}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--aur-accent)', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
                  {group}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {items.map(ind => (
                    <IndicatorRow
                      key={ind.id}
                      indicator={ind}
                      onToggle={handleToggle}
                      onParamChange={handleParamChange}
                      onResetSingle={handleResetSingle}
                      onEdit={() => setEditingIndicator(editingIndicator === ind.id ? null : ind.id)}
                      isEditing={editingIndicator === ind.id}
                    />
                  ))}
                </div>
              </GlassPanel>
            );
          })}
        </div>
      )}
    </div>
  );
};

interface IndicatorRowProps {
  indicator: IndicatorFullState;
  onToggle: (id: string) => void;
  onParamChange: (indicatorId: string, paramId: string, value: number) => void;
  onResetSingle: (indicatorId: string) => void;
  onEdit: () => void;
  isEditing: boolean;
}

const IndicatorRow: React.FC<IndicatorRowProps> = ({
  indicator,
  onToggle,
  onParamChange,
  onResetSingle,
  onEdit,
  isEditing,
}) => {
  const validation = validateIndicatorParams(indicator.id, indicator.params);

  return (
    <div
      className="aur-glass"
      style={{
        padding: '12px',
        borderLeft: `3px solid ${indicator.enabled ? 'var(--aur-positive)' : 'var(--aur-border)'}`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1 }}>
          {/* Toggle */}
          <button
            onClick={() => onToggle(indicator.id)}
            style={{
              width: '36px',
              height: '20px',
              borderRadius: '10px',
              border: 'none',
              background: indicator.enabled ? 'var(--aur-positive)' : 'var(--aur-surface)',
              cursor: 'pointer',
              position: 'relative',
              transition: 'background 0.2s',
            }}
            aria-label={`${indicator.enabled ? 'Disable' : 'Enable'} ${indicator.name}`}
            role="switch"
            aria-checked={indicator.enabled}
          >
            <div style={{
              width: '16px',
              height: '16px',
              borderRadius: '50%',
              background: 'white',
              position: 'absolute',
              top: '2px',
              left: indicator.enabled ? '18px' : '2px',
              transition: 'left 0.2s',
            }} />
          </button>

          {/* Name */}
          <span style={{ fontSize: '13px', fontWeight: 500, minWidth: '80px' }}>
            {indicator.name}
          </span>

          {/* Status badge */}
          <span style={{
            fontSize: '9px',
            padding: '1px 5px',
            borderRadius: '3px',
            background: indicator.overlay ? 'rgba(124, 158, 255, 0.15)' : 'rgba(255, 138, 101, 0.15)',
            color: indicator.overlay ? 'var(--aur-accent)' : 'var(--aur-accent-2)',
          }}>
            {indicator.overlay ? 'OVL' : 'PNL'}
          </span>

          {/* Raw values */}
          {indicator.enabled && indicator.status === 'ok' && indicator.values.length > 0 && (
            <div style={{ display: 'flex', gap: '12px', marginLeft: '8px' }}>
              {indicator.values.map(v => (
                <div key={v.seriesName} style={{ textAlign: 'right' }}>
                  <div style={{ fontSize: '12px', fontFamily: 'var(--aur-font-mono)', color: 'var(--aur-text)' }}>
                    {v.formatted}
                  </div>
                  <div style={{ fontSize: '9px', color: 'var(--aur-text-secondary)' }}>
                    {v.label}
                  </div>
                </div>
              ))}
            </div>
          )}

          {indicator.enabled && indicator.status === 'insufficient_data' && (
            <span style={{ fontSize: '11px', color: 'var(--aur-warning)', marginLeft: '8px' }}>
              INSUFFICIENT DATA (need {indicator.minDataLength} bars)
            </span>
          )}

          {indicator.enabled && indicator.status === 'unavailable' && (
            <span style={{ fontSize: '11px', color: 'var(--aur-negative)', marginLeft: '8px' }}>
              {!validation.valid ? validation.errors[0] : 'DATA UNAVAILABLE'}
            </span>
          )}

          {!indicator.enabled && (
            <span style={{ fontSize: '11px', color: 'var(--aur-text-secondary)', marginLeft: '8px' }}>
              —
            </span>
          )}
        </div>

        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          {indicator.paramDefs.length > 0 && (
            <button
              onClick={onEdit}
              className="aur-btn"
              style={{ fontSize: '10px', padding: '2px 8px' }}
              aria-label={`Configure ${indicator.name} parameters`}
            >
              {isEditing ? 'CLOSE' : 'CONFIG'}
            </button>
          )}
          <button
            onClick={() => onResetSingle(indicator.id)}
            className="aur-btn"
            style={{ fontSize: '10px', padding: '2px 8px' }}
            aria-label={`Reset ${indicator.name} to defaults`}
          >
            <RotateCcw size={10} />
          </button>
        </div>
      </div>

      {/* Parameter editor */}
      {isEditing && indicator.paramDefs.length > 0 && (
        <div style={{ marginTop: '10px', paddingTop: '10px', borderTop: '1px solid var(--aur-border)' }}>
          <div style={{ fontSize: '10px', color: 'var(--aur-text-secondary)', marginBottom: '6px' }}>
            PARAMETERS
          </div>
          {indicator.paramDefs.map(paramDef => {
            const currentValue = indicator.params[paramDef.id] ?? paramDef.default;
            return (
              <div key={paramDef.id} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
                <label
                  htmlFor={`param-${indicator.id}-${paramDef.id}`}
                  style={{ fontSize: '11px', color: 'var(--aur-ink-dim)', minWidth: '50px' }}
                >
                  {paramDef.label}
                </label>
                <input
                  id={`param-${indicator.id}-${paramDef.id}`}
                  type="number"
                  value={currentValue}
                  min={paramDef.min}
                  max={paramDef.max}
                  step={paramDef.step}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    if (!isNaN(val)) onParamChange(indicator.id, paramDef.id, val);
                  }}
                  style={{
                    width: '60px',
                    padding: '4px 6px',
                    background: 'var(--aur-surface)',
                    border: `1px solid ${!validation.valid ? 'var(--aur-negative)' : 'var(--aur-border)'}`,
                    borderRadius: '4px',
                    color: 'var(--aur-text)',
                    fontSize: '12px',
                    fontFamily: 'var(--aur-font-mono)',
                  }}
                  aria-label={`${paramDef.label} for ${indicator.name}`}
                />
                <span style={{ fontSize: '10px', color: 'var(--aur-text-secondary)' }}>
                  {paramDef.min}–{paramDef.max}
                </span>
              </div>
            );
          })}
          {!validation.valid && (
            <div style={{ marginTop: '6px', fontSize: '11px', color: 'var(--aur-negative)' }}>
              {validation.errors.join('; ')}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
