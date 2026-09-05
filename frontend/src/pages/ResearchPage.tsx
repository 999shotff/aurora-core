import React, { useEffect, useState } from 'react';
import { ResearchLab } from './ResearchLab';
import { ResearchWorkspace } from './ResearchWorkspace';
import { useEventBus } from '../lib/eventBus';

type Tab = 'lab' | 'workspace';

export const ResearchPage: React.FC = () => {
  const [tab, setTab] = useState<Tab>('lab');
  const { emit } = useEventBus();
  useEffect(() => { emit('navigation', 'Research opened', 'live'); }, [emit]);

  return (
    <div>
      <div style={{ display: 'flex', gap: 4, background: 'rgba(0,0,0,0.25)', border: '1px solid var(--aur-border-soft)', borderRadius: 10, padding: 4, marginBottom: 16, width: 'fit-content' }}>
        {(['lab', 'workspace'] as Tab[]).map(t => (
          <button
            key={t}
            onClick={() => setTab(t)}
            style={{
              background: tab === t ? 'var(--aur-glass-strong)' : 'none', border: 'none',
              color: tab === t ? 'var(--aur-ink)' : 'var(--aur-ink-dim)', fontSize: 12.5, fontWeight: 600,
              padding: '7px 16px', borderRadius: 7, cursor: 'pointer', textTransform: 'capitalize',
            }}
          >
            {t === 'lab' ? 'Research Lab' : 'Workspace'}
          </button>
        ))}
      </div>
      {tab === 'lab' ? <ResearchLab /> : <ResearchWorkspace />}
    </div>
  );
};
