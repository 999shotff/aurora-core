import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { createPortal } from 'react-dom';
import { Search, CornerDownLeft } from 'lucide-react';
import { GlassSurface } from '../ui/GlassSurface';

interface Command {
  id: string;
  label: string;
  hint?: string;
  action: () => void;
}

export const SearchCommand: React.FC = () => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIdx, setActiveIdx] = useState(0);
  const navigate = useNavigate();

  const commands: Command[] = useMemo(() => [
    { id: 'nav-command', label: 'Open Command Center', hint: 'Navigate', action: () => navigate('/') },
    { id: 'nav-geo', label: 'Open Geo Observatory', hint: 'Navigate', action: () => navigate('/geo') },
    { id: 'nav-market', label: 'Open Market Observatory', hint: 'Navigate', action: () => navigate('/market') },
    { id: 'nav-intel', label: 'Open Intelligence', hint: 'Navigate', action: () => navigate('/intelligence') },
    { id: 'nav-research', label: 'Open Research', hint: 'Navigate', action: () => navigate('/research') },
    { id: 'nav-evidence', label: 'Search evidence', hint: 'Navigate', action: () => navigate('/evidence') },
    { id: 'nav-neural', label: 'Open Neural Field', hint: 'Navigate', action: () => navigate('/neural') },
    { id: 'nav-reports', label: 'Open Reports', hint: 'Navigate', action: () => navigate('/reports') },
    { id: 'nav-settings', label: 'Open Settings', hint: 'Navigate', action: () => navigate('/settings') },
  ], [navigate]);

  const filtered = useMemo(() => {
    if (!query.trim()) return commands;
    const q = query.toLowerCase();
    return commands.filter(c => c.label.toLowerCase().includes(q));
  }, [commands, query]);

  const openPalette = () => { setQuery(''); setActiveIdx(0); setOpen(true); };
  const closePalette = () => setOpen(false);

  const handleQueryChange = (value: string) => { setQuery(value); setActiveIdx(0); };

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setOpen(o => {
          if (!o) { setQuery(''); setActiveIdx(0); }
          return !o;
        });
      } else if (e.key === 'Escape') {
        setOpen(o => (o ? false : o));
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const runActive = () => {
    const cmd = filtered[activeIdx];
    if (cmd) { cmd.action(); setOpen(false); }
  };

  if (!open) {
    return (
      <button
        onClick={openPalette}
        style={{
          display: 'flex', alignItems: 'center', gap: 8, background: 'var(--aur-glass-strong)',
          border: '1px solid var(--aur-border-soft)', color: 'var(--aur-ink-dim)', fontSize: 12.5,
          padding: '8px 12px', borderRadius: 10, cursor: 'pointer', minWidth: 0,
        }}
        aria-label="Open command palette"
      >
        <Search size={14} />
        <span className="aur-search-label">Search or jump to…</span>
        <kbd style={{ marginLeft: 6, fontSize: 10.5, background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: 5, border: '1px solid var(--aur-border-soft)' }}>⌘K</kbd>
      </button>
    );
  }

  return createPortal(
    <div
      onClick={closePalette}
      style={{ position: 'fixed', inset: 0, background: 'rgba(3,4,7,0.6)', zIndex: 200, display: 'flex', justifyContent: 'center', alignItems: 'flex-start', paddingTop: '12vh' }}
    >
        <GlassSurface
          as="div"
          variant="strong"
          rounding="lg"
          role="dialog"
          aria-label="Command palette"
          style={{
            width: 'min(560px, 92vw)', overflow: 'hidden', boxShadow: '0 24px 60px rgba(0,0,0,0.5)',
          }}
        >
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 16px', borderBottom: '1px solid var(--aur-border-soft)' }}>
          <Search size={16} color="var(--aur-ink-faint)" />
          <input
            ref={el => { if (el) el.focus(); }}
            value={query}
            onChange={e => handleQueryChange(e.target.value)}
            onKeyDown={e => {
              if (e.key === 'ArrowDown') { e.preventDefault(); setActiveIdx(i => Math.min(i + 1, filtered.length - 1)); }
              if (e.key === 'ArrowUp') { e.preventDefault(); setActiveIdx(i => Math.max(i - 1, 0)); }
              if (e.key === 'Enter') { e.preventDefault(); runActive(); }
            }}
            placeholder="Search investigations, evidence, or jump to a module…"
            style={{ flex: 1, background: 'none', border: 'none', outline: 'none', color: 'var(--aur-ink)', fontSize: 14 }}
          />
          <kbd style={{ fontSize: 10.5, background: 'rgba(255,255,255,0.06)', padding: '2px 6px', borderRadius: 5, border: '1px solid var(--aur-border-soft)' }}>ESC</kbd>
        </div>
        <div style={{ maxHeight: 340, overflowY: 'auto', padding: 6 }}>
          {filtered.length === 0 && (
            <div style={{ padding: '24px 16px', textAlign: 'center', fontSize: 13, color: 'var(--aur-ink-faint)' }}>No matches</div>
          )}
          {filtered.map((c, i) => (
            <button
              key={c.id}
              onClick={() => { c.action(); closePalette(); }}
              onMouseEnter={() => setActiveIdx(i)}
              style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%',
                padding: '10px 12px', borderRadius: 9, border: 'none', textAlign: 'left', cursor: 'pointer',
                background: i === activeIdx ? 'var(--aur-glass-strong)' : 'transparent',
                color: i === activeIdx ? 'var(--aur-ink)' : 'var(--aur-ink-dim)', fontSize: 13,
              }}
            >
              <span>{c.label}</span>
              {i === activeIdx ? <CornerDownLeft size={13} /> : <span style={{ fontSize: 10.5, color: 'var(--aur-ink-faint)' }}>{c.hint}</span>}
            </button>
          ))}
        </div>
        </GlassSurface>
      </div>,
    document.body
  );
};
