import React, { useEffect } from 'react';
import { NavLink } from 'react-router-dom';
import {
  Radar, Globe2, LineChart, BrainCircuit, FlaskConical, Shield,
  Share2, FileBarChart2, Settings as SettingsIcon, X,
} from 'lucide-react';
import { usePhysicsSheet } from '../../lib/usePhysicsSheet';

interface NavItem { to: string; label: string; icon: React.ReactNode; }
interface NavGroup { title: string; items: NavItem[]; }

const NAV_GROUPS: NavGroup[] = [
  { title: 'Command', items: [{ to: '/', label: 'Command Center', icon: <Radar size={17} /> }] },
  {
    title: 'Observe', items: [
      { to: '/geo', label: 'Geo Observatory', icon: <Globe2 size={17} /> },
      { to: '/market', label: 'Market Observatory', icon: <LineChart size={17} /> },
    ],
  },
  {
    title: 'Analyze', items: [
      { to: '/intelligence', label: 'Intelligence', icon: <BrainCircuit size={17} /> },
      { to: '/research', label: 'Research', icon: <FlaskConical size={17} /> },
      { to: '/evidence', label: 'Evidence', icon: <Shield size={17} /> },
    ],
  },
  { title: 'Visualize', items: [{ to: '/neural', label: 'Neural Field', icon: <Share2 size={17} /> }] },
  { title: 'Output', items: [{ to: '/reports', label: 'Reports', icon: <FileBarChart2 size={17} /> }] },
  { title: 'System', items: [{ to: '/settings', label: 'Settings', icon: <SettingsIcon size={17} /> }] },
];

interface AuroraSidebarProps {
  mobileOpen: boolean;
  onMobileOpenChange: (open: boolean) => void;
}

export const AuroraSidebar: React.FC<AuroraSidebarProps> = ({ mobileOpen, onMobileOpenChange }) => {
  const sheet = usePhysicsSheet({ edge: 'left', fallbackSize: 264 });
  const { elRef, pos, isOpen, open, close, onPointerDown } = sheet;

  useEffect(() => {
    if (mobileOpen) open(); else close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mobileOpen]);

  useEffect(() => {
    if (!isOpen && mobileOpen) onMobileOpenChange(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isOpen]);

  const isDesktop = () => window.innerWidth > 980;

  return (
    <>
      {mobileOpen && (
        <div
          onClick={() => onMobileOpenChange(false)}
          style={{ position: 'fixed', inset: 0, background: 'rgba(3,4,7,0.55)', zIndex: 55 }}
        />
      )}
      <aside
        ref={elRef}
        className="aur-sidebar"
        style={{
          position: 'fixed', top: 0, left: 0, bottom: 0, width: 'var(--aur-sidebar-w)',
          background: 'rgba(9,11,16,0.92)', backdropFilter: 'blur(22px) saturate(150%)', WebkitBackdropFilter: 'blur(22px) saturate(150%)',
          borderRight: '1px solid var(--aur-border-soft)', display: 'flex', flexDirection: 'column', padding: '18px 0',
          zIndex: 60, transform: `translateX(${isDesktop() ? 0 : pos}px)`, touchAction: 'none',
          willChange: 'transform',
        }}
        aria-label="Primary navigation"
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 18px 18px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 30, height: 30, borderRadius: 9, flexShrink: 0,
              background: 'linear-gradient(135deg, var(--aur-accent), var(--aur-accent-2))',
              display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, fontSize: 13, color: '#0A0B10',
              fontFamily: 'var(--aur-font-display)',
            }}>A</div>
            <div style={{ fontFamily: 'var(--aur-font-display)', fontSize: 14, fontWeight: 700, letterSpacing: '0.02em' }}>AURORA CORE</div>
          </div>
          <button
            onClick={() => onMobileOpenChange(false)}
            aria-label="Close navigation"
            className="aur-sidebar-close-btn"
            style={{
              display: 'flex', width: 30, height: 30, borderRadius: 9,
              background: 'var(--aur-glass)', border: '1px solid var(--aur-border-soft)', color: 'var(--aur-ink-dim)',
              alignItems: 'center', justifyContent: 'center', cursor: 'pointer',
            }}
          >
            <X size={14} />
          </button>
        </div>

        <nav style={{ display: 'flex', flexDirection: 'column', gap: 14, padding: '0 10px', overflowY: 'auto' }}>
          {NAV_GROUPS.map(group => (
            <div key={group.title}>
              <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: 'var(--aur-ink-faint)', padding: '0 10px 6px', textTransform: 'uppercase' }}>
                {group.title}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                {group.items.map(item => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    onClick={() => onMobileOpenChange(false)}
                    style={({ isActive }) => ({
                      display: 'flex', alignItems: 'center', gap: 11, padding: '9px 11px', borderRadius: 10,
                      color: isActive ? 'var(--aur-accent)' : 'var(--aur-ink-dim)', textDecoration: 'none',
                      fontSize: 13.5, fontWeight: 500,
                      background: isActive ? 'var(--aur-glass-strong)' : 'transparent',
                      boxShadow: isActive ? 'inset 0 0 0 1px var(--aur-border)' : 'none',
                      transition: 'background 0.15s, color 0.15s',
                    })}
                  >
                    {item.icon}
                    {item.label}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        <div
          onPointerDown={onPointerDown}
          aria-hidden="true"
          style={{ position: 'absolute', top: '50%', right: 4, transform: 'translateY(-50%)', width: 6, height: 56, borderRadius: 3, background: 'rgba(255,255,255,0.14)', cursor: 'grab', touchAction: 'none' }}
        />
      </aside>
    </>
  );
};
