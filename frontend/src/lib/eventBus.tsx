import React, { createContext, useCallback, useContext, useRef, useState } from 'react';
import type { ProcessingEvent, ProcessingEventKind, DataOrigin } from '../types/domain';

const MAX_EVENTS = 200;

interface EventBusValue {
  events: ProcessingEvent[];
  emit: (kind: ProcessingEventKind, label: string, origin: DataOrigin, detail?: string) => void;
}

const EventBusContext = createContext<EventBusValue | null>(null);

let idCounter = 0;
function nextId() {
  idCounter += 1;
  return `evt_${Date.now().toString(36)}_${idCounter}`;
}

export const EventBusProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [events, setEvents] = useState<ProcessingEvent[]>([]);
  const lastEmitRef = useRef<Record<string, number>>({});

  const emit = useCallback((kind: ProcessingEventKind, label: string, origin: DataOrigin, detail?: string) => {
    // Light de-dupe: identical label within 400ms (guards against effect double-fires in StrictMode)
    const key = kind + '::' + label;
    const now = Date.now();
    if (lastEmitRef.current[key] && now - lastEmitRef.current[key] < 400) return;
    lastEmitRef.current[key] = now;

    const event: ProcessingEvent = {
      id: nextId(),
      kind,
      label,
      detail,
      timestamp: new Date().toISOString(),
      origin,
    };
    setEvents(prev => [event, ...prev].slice(0, MAX_EVENTS));
  }, []);

  return (
    <EventBusContext.Provider value={{ events, emit }}>
      {children}
    </EventBusContext.Provider>
  );
};

export function useEventBus(): EventBusValue {
  const ctx = useContext(EventBusContext);
  if (!ctx) throw new Error('useEventBus must be used within EventBusProvider');
  return ctx;
}
