import React, { useEffect } from 'react';
import { GeoExplorer } from './GeoExplorer';
import { useEventBus } from '../lib/eventBus';

export const GeoObservatoryPage: React.FC = () => {
  const { emit } = useEventBus();
  useEffect(() => { emit('navigation', 'Geo Observatory opened', 'live'); }, [emit]);

  return (
    <div className="aur-geo-wrap">
      <GeoExplorer />
    </div>
  );
};
