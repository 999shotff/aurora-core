import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import './styles/tokens.css';
import { EventBusProvider } from './lib/eventBus';
import { DataModeProvider } from './lib/dataMode';
import { InspectorProvider } from './components/shell/InspectorSheet';
import { AppShell } from './components/shell/AppShell';
import { LoadingState } from './components/shell/primitives';

const CommandCenter = lazy(() => import('./pages/CommandCenter').then(m => ({ default: m.CommandCenter })));
const GeoObservatoryPage = lazy(() => import('./pages/GeoObservatoryPage').then(m => ({ default: m.GeoObservatoryPage })));
const MarketObservatoryPage = lazy(() => import('./pages/MarketObservatoryPage').then(m => ({ default: m.MarketObservatoryPage })));
const IntelligencePage = lazy(() => import('./pages/IntelligencePage').then(m => ({ default: m.IntelligencePage })));
const ResearchPage = lazy(() => import('./pages/ResearchPage').then(m => ({ default: m.ResearchPage })));
const EvidencePage = lazy(() => import('./pages/EvidencePage').then(m => ({ default: m.EvidencePage })));
const NeuralFieldPage = lazy(() => import('./pages/NeuralFieldPage').then(m => ({ default: m.NeuralFieldPage })));
const ReportsPage = lazy(() => import('./pages/ReportsPage').then(m => ({ default: m.ReportsPage })));
const SettingsPageWrapper = lazy(() => import('./pages/SettingsPageWrapper').then(m => ({ default: m.SettingsPageWrapper })));

function App() {
  return (
    <EventBusProvider>
      <DataModeProvider>
        <InspectorProvider>
          <BrowserRouter>
            <Suspense fallback={<div style={{ padding: 40 }}><LoadingState label="Loading module…" /></div>}>
              <Routes>
                <Route element={<AppShell />}>
                  <Route path="/" element={<CommandCenter />} />
                  <Route path="/geo" element={<GeoObservatoryPage />} />
                  <Route path="/market" element={<MarketObservatoryPage />} />
                  <Route path="/intelligence" element={<IntelligencePage />} />
                  <Route path="/research" element={<ResearchPage />} />
                  <Route path="/evidence" element={<EvidencePage />} />
                  <Route path="/neural" element={<NeuralFieldPage />} />
                  <Route path="/reports" element={<ReportsPage />} />
                  <Route path="/settings" element={<SettingsPageWrapper />} />
                  <Route path="*" element={<CommandCenter />} />
                </Route>
              </Routes>
            </Suspense>
          </BrowserRouter>
        </InspectorProvider>
      </DataModeProvider>
    </EventBusProvider>
  );
}

export default App;
