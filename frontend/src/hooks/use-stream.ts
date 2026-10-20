import { useState, useCallback, useEffect, useMemo, useRef } from 'react';
import { ws, launchCampaign, stopCampaign, pauseCampaign, resumeCampaign, retryCampaign, createCampaign, deleteCampaign, probeTarget, ingestDoc, deleteDoc, knowledgeStats, knowledgeEntries, reindexKnowledge, mutationDemos, listReports, deleteReport } from '../services/api';
import type { Campaign, CampaignRun, EventPayload, Finding, TargetDescriptor, Report, IngestDoc, MutationDemo } from '../types';

export function useStream(runId: string | null) {
  const [events, setEvents] = useState<EventPayload[]>([]);
  const [connected, setConnected] = useState(false);

  useCallback(() => {
    if (!runId) return;
    const socket = ws(runId);
    socket.onmessage = (ev) => {
      try {
        const payload = JSON.parse(ev.data) as EventPayload;
        setEvents((prev) => [payload, ...prev].slice(0, 500));
      } catch {
        // ignore malformed frames
      }
    };
    socket.onopen = () => setConnected(true);
    socket.onclose = () => setConnected(false);
    socket.onerror = () => setConnected(false);
    return () => socket.close();
  }, [runId]);

  return { events, connected };
}
