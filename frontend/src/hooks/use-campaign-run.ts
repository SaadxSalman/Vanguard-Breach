import { useCallback, useEffect, useMemo, useState } from 'react';
import { runDetail } from '../services/api';
import type { CampaignRun } from '../types';

export function useCampaignRun(runId: string | null) {
  const [run, setRun] = useState<CampaignRun | null>(null);
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!runId) return;
    setLoading(true);
    try {
      const data = await runDetail(runId);
      setRun(data);
    } catch {
      // network/404 handled at caller
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    if (!runId) return;
    let id: ReturnType<typeof setInterval>;
    refresh();
    id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [runId, refresh]);

  return { run, loading, refresh };
}
