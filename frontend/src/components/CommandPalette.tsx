import React, { useState, useEffect, useRef, useCallback } from 'react';

interface Command {
  id: string;
  label: string;
  section: string;
  action: () => void;
  shortcut?: string;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (page: string) => void;
}

const CommandPalette: React.FC<CommandPaletteProps> = ({ isOpen, onClose, onNavigate }) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const commands: Command[] = [
    { id: 'command', label: 'Command Center', section: 'Navigation', action: () => onNavigate('command'), shortcut: '⌘1' },
    { id: 'market', label: 'Market Observatory', section: 'Navigation', action: () => onNavigate('market'), shortcut: '⌘2' },
    { id: 'geo', label: 'Geo Observatory', section: 'Navigation', action: () => onNavigate('geo'), shortcut: '⌘3' },
    { id: 'intelligence', label: 'Intelligence', section: 'Navigation', action: () => onNavigate('intelligence'), shortcut: '⌘4' },
    { id: 'research', label: 'Research', section: 'Navigation', action: () => onNavigate('research'), shortcut: '⌘5' },
    { id: 'evidence', label: 'Evidence', section: 'Navigation', action: () => onNavigate('evidence'), shortcut: '⌘6' },
    { id: 'neuralfield', label: 'Neural Field', section: 'Navigation', action: () => onNavigate('neuralfield'), shortcut: '⌘7' },
    { id: 'reports', label: 'Reports', section: 'Navigation', action: () => onNavigate('reports'), shortcut: '⌘8' },
    { id: 'settings', label: 'Settings', section: 'Navigation', action: () => onNavigate('settings'), shortcut: '⌘9' },
    { id: 'landing', label: 'Home', section: 'Navigation', action: () => onNavigate('landing') },
  ];

  const filtered = commands.filter(cmd =>
    cmd.label.toLowerCase().includes(query.toLowerCase()) ||
    cmd.section.toLowerCase().includes(query.toLowerCase())
  );

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  useEffect(() => {
    const item = listRef.current?.children[selectedIndex] as HTMLElement;
    item?.scrollIntoView({ block: 'nearest' });
  }, [selectedIndex]);

  const execute = useCallback((cmd: Command) => {
    cmd.action();
    onClose();
  }, [onClose]);

  useEffect(() => {
    if (!isOpen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex(prev => Math.min(prev + 1, filtered.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex(prev => Math.max(prev - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (filtered[selectedIndex]) execute(filtered[selectedIndex]);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [isOpen, filtered, selectedIndex, execute, onClose]);

  if (!isOpen) return null;

  return (
    <div style={overlayStyle} onClick={onClose} role="dialog" aria-label="Command palette" aria-modal="true">
      <div style={paletteStyle} onClick={e => e.stopPropagation()}>
        <div style={inputContainerStyle}>
          <span style={searchIconStyle}>⌘</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={e => setQuery(e.target.value)}
            placeholder="Type a command..."
            style={inputStyle}
            aria-label="Search commands"
          />
        </div>
        <div ref={listRef} style={listStyle} role="listbox">
          {filtered.length === 0 && (
            <div style={emptyStyle}>No commands found</div>
          )}
          {filtered.map((cmd, i) => (
            <button
              key={cmd.id}
              style={i === selectedIndex ? itemActiveStyle : itemStyle}
              onClick={() => execute(cmd)}
              onMouseEnter={() => setSelectedIndex(i)}
              role="option"
              aria-selected={i === selectedIndex}
            >
              <span>{cmd.label}</span>
              <span style={metaStyle}>
                {cmd.shortcut && <span style={shortcutStyle}>{cmd.shortcut}</span>}
                <span style={sectionStyle}>{cmd.section}</span>
              </span>
            </button>
          ))}
        </div>
        <div style={footerStyle}>
          <span style={footerKeyStyle}>↑↓</span> navigate
          <span style={footerKeyStyle}>↵</span> select
          <span style={footerKeyStyle}>esc</span> close
        </div>
      </div>
    </div>
  );
};

const overlayStyle: React.CSSProperties = {
  position: 'fixed',
  inset: 0,
  background: 'rgba(0, 0, 0, 0.6)',
  backdropFilter: 'blur(4px)',
  display: 'flex',
  justifyContent: 'center',
  paddingTop: '20vh',
  zIndex: 9999,
};

const paletteStyle: React.CSSProperties = {
  width: '520px',
  maxHeight: '400px',
  background: '#161b22',
  border: '1px solid #30363d',
  borderRadius: '12px',
  boxShadow: '0 16px 70px rgba(0, 0, 0, 0.5)',
  display: 'flex',
  flexDirection: 'column',
  overflow: 'hidden',
};

const inputContainerStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  padding: '12px 16px',
  borderBottom: '1px solid #21262d',
};

const searchIconStyle: React.CSSProperties = {
  color: '#8b949e',
  fontSize: '14px',
  marginRight: '10px',
  fontWeight: 700,
};

const inputStyle: React.CSSProperties = {
  flex: 1,
  background: 'transparent',
  border: 'none',
  outline: 'none',
  color: '#e6edf3',
  fontSize: '14px',
  fontFamily: 'inherit',
};

const listStyle: React.CSSProperties = {
  flex: 1,
  overflow: 'auto',
  padding: '4px',
};

const itemStyle: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
  width: '100%',
  padding: '8px 12px',
  background: 'transparent',
  border: 'none',
  borderRadius: '6px',
  color: '#c9d1d9',
  fontSize: '13px',
  cursor: 'pointer',
  textAlign: 'left',
};

const itemActiveStyle: React.CSSProperties = {
  ...itemStyle,
  background: 'rgba(38, 166, 154, 0.1)',
};

const metaStyle: React.CSSProperties = {
  display: 'flex',
  gap: '8px',
  alignItems: 'center',
};

const shortcutStyle: React.CSSProperties = {
  padding: '2px 6px',
  borderRadius: '4px',
  background: '#21262d',
  fontSize: '10px',
  color: '#8b949e',
  fontFamily: 'monospace',
};

const sectionStyle: React.CSSProperties = {
  fontSize: '10px',
  color: '#484f58',
};

const emptyStyle: React.CSSProperties = {
  padding: '20px',
  textAlign: 'center',
  color: '#484f58',
  fontSize: '12px',
};

const footerStyle: React.CSSProperties = {
  padding: '8px 16px',
  borderTop: '1px solid #21262d',
  fontSize: '11px',
  color: '#484f58',
  display: 'flex',
  gap: '8px',
  alignItems: 'center',
};

const footerKeyStyle: React.CSSProperties = {
  padding: '1px 4px',
  borderRadius: '3px',
  background: '#21262d',
  fontSize: '10px',
  fontFamily: 'monospace',
  color: '#8b949e',
  marginLeft: '8px',
};

export { CommandPalette };
