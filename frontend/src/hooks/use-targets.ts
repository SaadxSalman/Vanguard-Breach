import { useCallback, useEffect, useMemo, useState } from 'react';
import { targets, targetDetail, probeTarget } from '../services/api';
import type { TargetDescriptor, ProbeRequest } from '../types';

export function useTargets() {
  const [items, setItems] = useState<TargetDescriptor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await targets();
      setItems(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { targets: items, loading, error, refresh };
}

export function useTarget(id: string) {
  const [item, setItem] = useState<TargetDescriptor | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await targetDetail(id);
      setItem(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { target: item, loading, error, refresh };
}

export function useProbe() {
  const [loading, setLoading] = useState(false);
  const [response, setResponse] = useState<Record<string, unknown> | null>(null);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (payload: ProbeRequest) => {
    setLoading(true);
    setError(null);
    setResponse(null);
    try {
      const data = await probeTarget(payload);
      setResponse(data.response);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  return { response, error, loading, run };
}
