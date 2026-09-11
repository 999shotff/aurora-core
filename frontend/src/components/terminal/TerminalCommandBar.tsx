/**
 * AURORA Terminal — Command Bar.
 *
 * Allowlisted command registry. Routes commands to existing AURORA modules.
 * No arbitrary shell execution. No unrestricted agents.
 */

import React, { useState, useCallback, useMemo, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, CornerDownLeft, ArrowRight } from 'lucide-react';
import { GlassSurface } from '../ui/GlassSurface';
import { executeTerminalCommand, type CommandResult } from '../../services/terminal';

const LOCAL_COMMANDS = [
  { id: 'OPEN_MARKET', label: 'Market Observatory', hint: '/market', keywords: ['market', 'chart', 'price', 'candle'] },
  { id: 'OPEN_GEO', label: 'Geo Observatory', hint: '/geo', keywords: ['geo', 'satellite', 'observation'] },
  { id: 'OPEN_INTELLIGENCE', label: 'Intelligence', hint: '/intelligence', keywords: ['intelligence', 'reason', 'analysis'] },
  { id: 'OPEN_INVESTIGATIONS', label: 'Investigations', hint: '/investigations', keywords: ['investigate', 'investigation'] },
  { id: 'OPEN_SYNTHESIS', label: 'Synthesis', hint: '/synthesis', keywords: ['synthesis', 'synthesize'] },
  { id: 'OPEN_EVIDENCE', label: 'Evidence', hint: '/evidence', keywords: ['evidence', 'graph'] },
  { id: 'OPEN_MEMORY', label: 'Memory', hint: '/memory', keywords: ['memory', 'retrieve'] },
  { id: 'OPEN_COMPUTE', label: 'Compute Fabric', hint: '/compute', keywords: ['compute', 'gpu', 'worker'] },
  { id: 'OPEN_REPORTS', label: 'Reports', hint: '/reports', keywords: ['report', 'export'] },
  { id: 'OPEN_NEURAL', label: 'Neural Field', hint: '/neural', keywords: ['neural', 'pipeline'] },
  { id: 'OPEN_RESEARCH', label: 'Research', hint: '/research', keywords: ['research', 'hypothesis'] },
  { id: 'OPEN_INDICATORS', label: 'Indicators', hint: '/indicators', keywords: ['indicator', 'rsi', 'macd'] },
  { id: 'OPEN_SETTINGS', label: 'Settings', hint: '/settings', keywords: ['settings', 'config'] },
  { id: 'OPEN_COMMAND_CENTER', label: 'Command Center', hint: '/', keywords: ['command', 'center', 'home'] },
];

interface TerminalCommandBarProps {
  onCommandResult?: (result: CommandResult) => void;
}

export const TerminalCommandBar: React.FC<TerminalCommandBarProps> = ({ onCommandResult }) => {
  const [query, setQuery] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const filtered = useMemo(() => {
    if (!query.trim()) return LOCAL_COMMANDS;
    const q = query.toLowerCase();
    return LOCAL_COMMANDS.filter(
      c =>
        c.label.toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q) ||
        c.keywords.some(k => k.includes(q))
    );
  }, [query]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsOpen(o => !o);
      } else if (e.key === 'Escape') {
        setIsOpen(false);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus();
      setQuery('');
      setActiveIdx(0);
    }
  }, [isOpen]);

  const runCommand = useCallback(
    async (cmd: string) => {
      if (!cmd.trim()) return;
      try {
        const result = await executeTerminalCommand(cmd);
        onCommandResult?.(result);
        if (result.status === 'ok' && result.target) {
          navigate(result.target);
        }
      } catch {
        // Backend unreachable — fall back to local navigation
        const local = LOCAL_COMMANDS.find(c => c.id === cmd.toUpperCase());
        if (local) {
          navigate(local.hint);
        }
      }
      setIsOpen(false);
      setQuery('');
    },
    [navigate, onCommandResult]
  );

  const runActive = () => {
    const cmd = filtered[activeIdx];
    if (cmd) runCommand(cmd.id);
  };

  return (
    <>
      {/* Trigger button */}
      <button
        onClick={() => setIsOpen(true)}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          background: 'var(--aur-glass-strong)',
          border: '1px solid var(--aur-border-soft)',
          color: 'var(--aur-ink-dim)',
          fontSize: 12.5,
          padding: '8px 12px',
          borderRadius: 10,
          cursor: 'pointer',
          flex: 1,
          minWidth: 0,
        }}
        aria-label="Open command bar"
      >
        <Search size={14} />
        <span>Command Bar</span>
        <kbd
          style={{
            marginLeft: 6,
            fontSize: 10.5,
            background: 'rgba(255,255,255,0.06)',
            padding: '2px 6px',
            borderRadius: 5,
            border: '1px solid var(--aur-border-soft)',
          }}
        >
          ⌘K
        </kbd>
      </button>

      {/* Command palette overlay */}
      {isOpen && (
        <div
          onClick={() => setIsOpen(false)}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(3,4,7,0.6)',
            zIndex: 200,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'flex-start',
            paddingTop: '12vh',
          }}
        >
          <GlassSurface
            as="div"
            variant="strong"
            rounding="lg"
            role="dialog"
            aria-label="Command bar"
            onClick={e => e.stopPropagation()}
            style={{
              width: 'min(560px, 92vw)',
              overflow: 'hidden',
              boxShadow: '0 24px 60px rgba(0,0,0,0.5)',
            }}
          >
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 10,
                padding: '14px 16px',
                borderBottom: '1px solid var(--aur-border-soft)',
              }}
            >
              <Search size={16} color="var(--aur-ink-faint)" />
              <input
                ref={inputRef}
                value={query}
                onChange={e => {
                  setQuery(e.target.value);
                  setActiveIdx(0);
                }}
                onKeyDown={e => {
                  if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    setActiveIdx(i => Math.min(i + 1, filtered.length - 1));
                  }
                  if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    setActiveIdx(i => Math.max(i - 1, 0));
                  }
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    runActive();
                  }
                }}
                placeholder="Type a command: BTC-USD, OPEN MARKET, SYNTHESIZE..."
                style={{
                  flex: 1,
                  background: 'none',
                  border: 'none',
                  outline: 'none',
                  color: 'var(--aur-ink)',
                  fontSize: 14,
                }}
              />
              <kbd
                style={{
                  fontSize: 10.5,
                  background: 'rgba(255,255,255,0.06)',
                  padding: '2px 6px',
                  borderRadius: 5,
                  border: '1px solid var(--aur-border-soft)',
                }}
              >
                ESC
              </kbd>
            </div>
            <div style={{ maxHeight: 340, overflowY: 'auto', padding: 6 }}>
              {filtered.length === 0 && (
                <div
                  style={{
                    padding: '24px 16px',
                    textAlign: 'center',
                    fontSize: 13,
                    color: 'var(--aur-ink-faint)',
                  }}
                >
                  No matching commands
                </div>
              )}
              {filtered.map((c, i) => (
                <button
                  key={c.id}
                  onClick={() => runCommand(c.id)}
                  onMouseEnter={() => setActiveIdx(i)}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    width: '100%',
                    padding: '10px 12px',
                    borderRadius: 9,
                    border: 'none',
                    textAlign: 'left',
                    cursor: 'pointer',
                    background: i === activeIdx ? 'var(--aur-glass-strong)' : 'transparent',
                    color: i === activeIdx ? 'var(--aur-ink)' : 'var(--aur-ink-dim)',
                    fontSize: 13,
                  }}
                >
                  <span>{c.label}</span>
                  {i === activeIdx ? (
                    <CornerDownLeft size={13} />
                  ) : (
                    <span style={{ fontSize: 10.5, color: 'var(--aur-ink-faint)' }}>{c.hint}</span>
                  )}
                </button>
              ))}
            </div>
          </GlassSurface>
        </div>
      )}
    </>
  );
};

export default TerminalCommandBar;
