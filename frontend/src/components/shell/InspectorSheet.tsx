import React, { createContext, useCallback, useContext, useState } from 'react';
import { X } from 'lucide-react';
import { usePhysicsSheet } from '../../lib/usePhysicsSheet';

interface InspectorContent {
  title: string;
  body: React.ReactNode;
}

interface InspectorContextValue {
  openInspector: (content: InspectorContent) => void;
  closeInspector: () => void;
}

const InspectorContext = createContext<InspectorContextValue | null>(null);

export function useInspector(): InspectorContextValue {
  const ctx = useContext(InspectorContext);
  if (!ctx) throw new Error('useInspector must be used within InspectorProvider');
  return ctx;
}

export const InspectorProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const sheet = usePhysicsSheet({ edge: 'right', fallbackSize: 440 });
  const { elRef, pos, isOpen, onPointerDown } = sheet;
  const [content, setContent] = useState<InspectorContent | null>(null);

  const openInspector = useCallback((c: InspectorContent) => {
    setContent(c);
    sheet.open();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const closeInspector = useCallback(() => sheet.close(), [sheet]);

  return (
    <InspectorContext.Provider value={{ openInspector, closeInspector }}>
      {children}
      {sheet.isOpen && (
        <div onClick={closeInspector} style={{ position: 'fixed', inset: 0, background: 'rgba(3,4,7,0.5)', zIndex: 70 }} />
      )}
      <aside
        ref={elRef}
        className="aur-glass aur-glass--strong"
        style={{
          position: 'fixed', top: 0, right: 0, bottom: 0, width: 'var(--aur-sheet-w)',
          zIndex: 71, transform: `translateX(${pos}px)`,
          display: 'flex', flexDirection: 'column', touchAction: 'none', willChange: 'transform',
          borderRadius: 0,
        }}
        role="dialog"
        aria-label={content?.title ?? 'Inspector'}
        aria-hidden={!isOpen}
      >
        <div onPointerDown={onPointerDown} style={{ display: 'flex', justifyContent: 'center', padding: '12px 0 6px', cursor: 'grab' }}>
          <span style={{ width: 38, height: 4, borderRadius: 3, background: 'rgba(255,255,255,0.16)' }} />
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 22px 16px', borderBottom: '1px solid var(--aur-border-soft)' }}>
          <h3 style={{ fontSize: 16, fontWeight: 600, fontFamily: 'var(--aur-font-display)' }}>{content?.title ?? ''}</h3>
          <button
            onClick={closeInspector}
            aria-label="Close inspector"
            style={{ width: 30, height: 30, borderRadius: 9, background: 'var(--aur-glass)', border: '1px solid var(--aur-border-soft)', color: 'var(--aur-ink-dim)', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}
          >
            <X size={14} />
          </button>
        </div>
        <div style={{ padding: '20px 22px', overflowY: 'auto', flex: 1 }}>
          {content?.body}
        </div>
      </aside>
    </InspectorContext.Provider>
  );
};

/* Small helpers for consistent inspector body content */
export const InspectorSectionTitle: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <h4 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '0.05em', color: 'var(--aur-ink-faint)', fontWeight: 700, margin: '18px 0 10px' }}>{children}</h4>
);

export const InspectorRow: React.FC<{ label: string; value: React.ReactNode }> = ({ label, value }) => (
  <div style={{ display: 'flex', justifyContent: 'space-between', padding: '9px 0', borderBottom: '1px solid var(--aur-border-soft)', fontSize: 13 }}>
    <span>{label}</span>
    <span style={{ color: 'var(--aur-ink-dim)' }}>{value}</span>
  </div>
);
