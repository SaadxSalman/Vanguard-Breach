import { useCallback, useEffect, useState } from 'react';
import { targets, knowledgeStats, knowledgeEntries, reindexKnowledge, mutationDemos, ingestDoc } from '../services/api';
import type { MutationDemo as DemoMap, TargetDescriptor, KnowledgeStats as Stats, IngestionDoc } from '../types';

export function useKnowledge() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [entries, setEntries] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [s, e] = await Promise.all([knowledgeStats(), knowledgeEntries()]);
      setStats(s);
      setEntries(e);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { stats, entries, loading, error, refresh };
}

export function useDemos() {
  const [demos, setDemos] = useState<DemoMap>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await mutationDemos();
      setDemos(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { demos, loading, error, refresh };
}

export function useIngest() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const run = useCallback(async (doc: IngestionDoc) => {
    setLoading(true);
    setError(null);
    try {
      const data = await ingestDoc(doc);
      return data;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  return { ingest: run, loading, error };
}

export function useTargets() {
  const [items, setItems] = useState<TargetDescriptor[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await targets();
      setItems(data);
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
