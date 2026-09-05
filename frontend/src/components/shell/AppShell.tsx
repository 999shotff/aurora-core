import React, { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { AuroraSidebar } from './AuroraSidebar';
import { AppTopBar } from './AppTopBar';

const TITLES: Record<string, { title: string; subtitle: string }> = {
  '/': { title: 'Command Center', subtitle: 'System overview' },
  '/geo': { title: 'Geo Observatory', subtitle: 'Geospatial observation & change detection' },
  '/market': { title: 'Market Observatory', subtitle: 'Market data, indicators & structure' },
  '/intelligence': { title: 'Intelligence', subtitle: 'Question → evidence → analysis → conclusion' },
  '/research': { title: 'Research', subtitle: 'Investigations & workspace' },
  '/evidence': { title: 'Evidence', subtitle: 'Source records & provenance' },
  '/neural': { title: 'Neural Field', subtitle: 'Live processing pipeline visualization' },
  '/reports': { title: 'Reports', subtitle: 'Generated findings & exports' },
  '/settings': { title: 'Settings', subtitle: 'Workspace, data sources & appearance' },
};

export const AppShell: React.FC = () => {
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [online, setOnline] = useState(navigator.onLine);
  const location = useLocation();
  const meta = TITLES[location.pathname] ?? { title: 'Aurora Core', subtitle: '' };

  useEffect(() => {
    const on = () => setOnline(true);
    const off = () => setOnline(false);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); };
  }, []);

  return (
    <div className="aur-shell">
      <div className="aur-edge-zone" onClick={() => setMobileNavOpen(true)} />
      <AuroraSidebar mobileOpen={mobileNavOpen} onMobileOpenChange={setMobileNavOpen} />
      <main className="aur-main">
        <AppTopBar
          title={meta.title}
          subtitle={meta.subtitle}
          onOpenMobileNav={() => setMobileNavOpen(true)}
          connectionOk={online}
        />
        <Outlet />
      </main>
    </div>
  );
};
