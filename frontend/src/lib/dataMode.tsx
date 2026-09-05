import React, { createContext, useCallback, useContext, useState } from 'react';

type DataMode = 'demo' | 'live';

interface DataModeContextValue {
  dataMode: DataMode;
  setDataMode: (mode: DataMode) => void;
}

const DataModeContext = createContext<DataModeContextValue | null>(null);

export const DataModeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [dataMode, setDataModeState] = useState<DataMode>(
    () => (localStorage.getItem('aurora_data_mode') as DataMode) || 'live'
  );
  const setDataMode = useCallback((mode: DataMode) => {
    localStorage.setItem('aurora_data_mode', mode);
    setDataModeState(mode);
  }, []);
  return (
    <DataModeContext.Provider value={{ dataMode, setDataMode }}>
      {children}
    </DataModeContext.Provider>
  );
};

export function useDataMode(): DataModeContextValue {
  const ctx = useContext(DataModeContext);
  if (!ctx) throw new Error('useDataMode must be used within DataModeProvider');
  return ctx;
}
