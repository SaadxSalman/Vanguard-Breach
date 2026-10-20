import { useRef, useEffect, useState } from 'react';
import { useStream } from '../hooks/use-stream';
import type { EventPayload } from '../types';

const LEVEL_STYLES: Record<string, string> = {
  info: 'alert--info',
  warning: 'alert--warning',
  error: 'alert--error',
  debug: 'alert--debug',
  ping: 'alert--debug',
};

export function EventStream({ runId }: { runId: string }) {
  const [events, setEvents] = useState<EventPayload[]>([]);
  const { connected } = useStream(runId);

  useEffect(() => {
    if (!runId) return;
    const socket = new WebSocket(`${connected ? 'wss' : 'ws'}://${window.location.host}/ws/runs/${runId}`);
    socket.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data) as EventPayload;
        setEvents((prev) => [payload, ...prev].slice(0, 500));
      } catch {
        // ignore malformed frames
      }
    };
    socket.onopen = () => {};
    socket.onclose = () => {};
    return () => socket.close();
  }, [runId, connected]);

  if (!runId) return <div className="muted">No run selected.</div>;

  return (
    <div className="event-stream">
      <div className="event-stream__header">
        <h3>Live event stream</h3>
        <span className={`badge badge--${connected ? 'success' : 'warning'}`}>{connected ? 'connected' : 'connecting…'}</span>
      </div>
      <div className="event-stream__log">
        {events.map((ev, i) => (
          <Fragment key={`${ev.node}-${ev.ts}-${i}`}>
            <div className={`event-stream__row ${LEVEL_STYLES[ev.level] ?? ''}`}>
              <span className="event-stream__node">{ev.node}</span>
              <span className="event-stream__agent">{ev.agent}</span>
              <span className="event-stream__msg">{ev.message}</span>
            </div>
            {Object.keys(ev.data || {}).length > 0 && (
              <pre className="event-stream__data">{JSON.stringify(ev.data, null, 2)}</pre>
            )}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
