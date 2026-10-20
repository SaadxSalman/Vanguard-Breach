import { useCallback, useEffect, useState } from 'react';
import { createCampaign, deleteCampaign, launchCampaign, stopCampaign, pauseCampaign, resumeCampaign, retryCampaign, reports, deleteReport, reindexKnowledge, settings, knowledgeStats, ingestDoc } from '../services/api';
import type { Campaign, Report, KnowledgeStats } from '../types';

export function useCampaignsCrud() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const create = useCallback(async (body: Omit<Campaign, 'id' | 'created_at' | 'updated_at' | 'latest_run'>) => {
    setLoading(true);
    setError(null);
    try {
      return await createCampaign(body);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const del = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await deleteCampaign(id);
      return res.ok;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const launch = useCallback(async (id: string, opts?: { seed?: number; max_iterations?: number; severity_threshold?: number }) => {
    setLoading(true);
    setError(null);
    try {
      return await launchCampaign(id, opts);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const stop = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await stopCampaign(id);
      return res.ok;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const pause = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await pauseCampaign(id);
      return res.ok;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const resume = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await resumeCampaign(id);
      return res.ok;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  const retry = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await retryCampaign(id);
      return res.ok;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, []);

  return { create, del, launch, stop, pause, resume, retry, loading, error };
}

export function useReports() {
  const [loading, setLoading] = useState(false);
  const [reportsList, setReportsList] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listReports();
      setReportsList(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const remove = useCallback(async (id: string) => {
    setLoading(true);
    setError(null);
    try {
      const res = await deleteReport(id);
      if (res.ok) refresh();
      return res.ok;
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
      throw e;
    } finally {
      setLoading(false);
    }
  }, [refresh]);

  return { reports: reportsList, loading, error, refresh, remove };
}

export function useReport(runId: string) {
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await reports(runId);
      setReport(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    load();
  }, [runId, load]);

  return { report, loading, error, refresh: load };
}
