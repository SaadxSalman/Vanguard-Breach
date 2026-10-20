import { useCallback, useEffect, useMemo, useState } from 'react';
import type { Campaign, CampaignRun, Finding, RunDetail } from '../types';
import { campaign, runDetail, findings as fetchFindings } from '../services/api';

export function useCampaigns() {
  const [items, setItems] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await campaigns();
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

  return { campaigns: items, loading, error, refresh };
}

export function useCampaign(id: string) {
  const [item, setItem] = useState<Campaign | null>(null);
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const [c, r] = await Promise.all([campaign(id), runDetail(id)]);
      setItem(c);
      setRun(r);
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

  return { campaign: item, run, loading, error, refresh };
}

export function useFindings(runId?: string) {
  const [items, setItems] = useState<Finding[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const data = await fetchFindings(runId);
      setItems(data);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return { findings: items, loading, error, refresh };
}
