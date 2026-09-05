import React, { useEffect, useMemo, useState } from 'react';
import { GlassPanel } from '../components/shell/primitives';
import { useEventBus } from '../lib/eventBus';
import type { NeuralStage, ProcessingEventKind } from '../types/domain';

const STAGE_ORDER: NeuralStage[] = ['perception', 'ingestion', 'feature_extraction', 'domain_analysis', 'evidence_graph', 'synthesis', 'result'];

const STAGE_LABEL: Record<NeuralStage, string> = {
  perception: 'Perception',
  ingestion: 'Data ingestion',
  feature_extraction: 'Feature extraction',
  domain_analysis: 'Domain analysis',
  evidence_graph: 'Evidence graph',
  synthesis: 'Synthesis',
  result: 'Result',
};

const STAGE_COLOR: Record<NeuralStage, string> = {
  perception: '#5AC8E8',
  ingestion: '#5AC8E8',
  feature_extraction: '#A78BFA',
  domain_analysis: '#A78BFA',
  evidence_graph: '#FF8A65',
  synthesis: '#A78BFA',
  result: '#34D399',
};

const KIND_TO_STAGE: Record<ProcessingEventKind, NeuralStage> = {
  navigation: 'perception',
  connection: 'ingestion',
  data_fetch: 'ingestion',
  indicator_toggle: 'feature_extraction',
  structure_analysis: 'domain_analysis',
  evidence_indexed: 'evidence_graph',
  synthesis: 'synthesis',
};

const ACTIVE_WINDOW_MS = 2600;

// Layout: 7 stage nodes on a gentle arc, sized for a 900x360 viewBox.
const NODE_POS: Record<NeuralStage, { x: number; y: number }> = {
  perception: { x: 70, y: 200 },
  ingestion: { x: 205, y: 130 },
  feature_extraction: { x: 350, y: 200 },
  domain_analysis: { x: 495, y: 130 },
  evidence_graph: { x: 495, y: 270 },
  synthesis: { x: 650, y: 200 },
  result: { x: 810, y: 200 },
};

const EDGES: [NeuralStage, NeuralStage][] = [
  ['perception', 'ingestion'],
  ['ingestion', 'feature_extraction'],
  ['feature_extraction', 'domain_analysis'],
  ['feature_extraction', 'evidence_graph'],
  ['domain_analysis', 'synthesis'],
  ['evidence_graph', 'synthesis'],
  ['synthesis', 'result'],
];

export const NeuralFieldPage: React.FC = () => {
  const { events, emit } = useEventBus();
  const [selected, setSelected] = useState<NeuralStage | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => { emit('navigation', 'Neural Field opened', 'live'); }, [emit]);

  // Tick a real "now" value periodically so pulse windows fade out even with
  // no new events — used as a plain dependency, not called live inside useMemo.
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 400);
    return () => clearInterval(id);
  }, []);

  const activeStages = useMemo(() => {
    const set = new Set<NeuralStage>();
    for (const e of events) {
      if (now - new Date(e.timestamp).getTime() > ACTIVE_WINDOW_MS) break; // events are newest-first
      set.add(KIND_TO_STAGE[e.kind]);
    }
    return set;
  }, [events, now]);

  const lastEventForStage = (stage: NeuralStage) => events.find(e => KIND_TO_STAGE[e.kind] === stage);

  return (
    <div>
      <GlassPanel style={{ marginBottom: 14 }}>
        <p style={{ fontSize: 12.5, color: 'var(--aur-ink-dim)', lineHeight: 1.6 }}>
          This graph reflects real application events from this session — asset selection, data fetches, indicator toggles, and
          navigation — mapped onto Aurora's conceptual processing pipeline. Nodes pulse when a matching event occurs; there is no
          fabricated "thinking" animation. Interact with Market Observatory or Evidence in another tab and return here to see it react.
        </p>
      </GlassPanel>

      <GlassPanel style={{ marginBottom: 14 }}>
        <svg viewBox="0 0 900 360" width="100%" height="360" role="img" aria-label="Neural field pipeline diagram">
          <defs>
            <filter id="glow" x="-60%" y="-60%" width="220%" height="220%">
              <feGaussianBlur stdDeviation="6" result="blur" />
              <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>

          {EDGES.map(([from, to], i) => {
            const a = NODE_POS[from], b = NODE_POS[to];
            const active = activeStages.has(from) && activeStages.has(to);
            return (
              <line
                key={i} x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke={active ? 'rgba(124,158,255,0.6)' : 'rgba(255,255,255,0.08)'}
                strokeWidth={active ? 2 : 1.2}
                style={{ transition: 'stroke 0.4s' }}
              />
            );
          })}

          {STAGE_ORDER.map(stage => {
            const pos = NODE_POS[stage];
            const active = activeStages.has(stage);
            const color = STAGE_COLOR[stage];
            return (
              <g key={stage} onClick={() => setSelected(stage)} style={{ cursor: 'pointer' }}>
                {active && <circle cx={pos.x} cy={pos.y} r={26} fill={color} fillOpacity={0.18} filter="url(#glow)" />}
                <circle
                  cx={pos.x} cy={pos.y} r={16}
                  fill={active ? color : 'rgba(255,255,255,0.06)'}
                  stroke={selected === stage ? '#EDEFF3' : active ? color : 'rgba(255,255,255,0.16)'}
                  strokeWidth={selected === stage ? 2 : 1.4}
                  style={{ transition: 'fill 0.4s, stroke 0.2s' }}
                />
                <text x={pos.x} y={pos.y + 34} textAnchor="middle" fontSize="11" fontFamily="Inter, sans-serif" fill={active ? '#EDEFF3' : '#5B6273'}>
                  {STAGE_LABEL[stage]}
                </text>
              </g>
            );
          })}
        </svg>
      </GlassPanel>

      <GlassPanel>
        <h2 style={{ fontSize: 14, fontWeight: 600, marginBottom: 10 }}>
          {selected ? `${STAGE_LABEL[selected]} — last event` : 'Select a node to inspect its most recent event'}
        </h2>
        {selected && (() => {
          const ev = lastEventForStage(selected);
          if (!ev) return <p style={{ fontSize: 12.5, color: 'var(--aur-ink-faint)' }}>No events recorded yet for this stage this session.</p>;
          return (
            <div style={{ fontSize: 12.5, color: 'var(--aur-ink-dim)' }}>
              <div style={{ color: 'var(--aur-ink)', fontWeight: 500, marginBottom: 4 }}>{ev.label}</div>
              {ev.detail && <div>{ev.detail}</div>}
              <div style={{ marginTop: 6, fontSize: 11, color: 'var(--aur-ink-faint)' }}>{new Date(ev.timestamp).toLocaleTimeString()}</div>
            </div>
          );
        })()}
      </GlassPanel>
    </div>
  );
};
