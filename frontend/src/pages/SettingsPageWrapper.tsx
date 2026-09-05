import React, { useEffect } from 'react';
import { SettingsPage } from './SettingsPage';
import { useDataMode } from '../lib/dataMode';
import { useEventBus } from '../lib/eventBus';

export const SettingsPageWrapper: React.FC = () => {
  const { dataMode, setDataMode } = useDataMode();
  const { emit } = useEventBus();
  useEffect(() => { emit('navigation', 'Settings opened', 'live'); }, [emit]);

  return <SettingsPage dataMode={dataMode} onDataModeChange={setDataMode} />;
};
