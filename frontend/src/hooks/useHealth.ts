import { useCallback, useEffect, useState } from "react";
import type { HealthResponse } from "../types/api";

export interface UseHealthResult {
  data: HealthResponse | null;
  isLoading: boolean;
  error: string | null;
  latencyMs: number | null;
  lastChecked: Date | null;
  refetch: () => Promise<void>;
}

export function useHealth(apiUrl: string = "/api/health"): UseHealthResult {
  const [data, setData] = useState<HealthResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [latencyMs, setLatencyMs] = useState<number | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const fetchHealth = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    const start = performance.now();

    try {
      const response = await fetch(apiUrl, {
        headers: { Accept: "application/json" },
      });

      const elapsed = Math.round(performance.now() - start);
      setLatencyMs(elapsed);
      setLastChecked(new Date());

      if (!response.ok) {
        let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
        try {
          const errorJson = await response.json();
          if (errorJson.detail) {
            errorDetail = errorJson.detail;
          }
        } catch {
          // ignore json parse error on non-json error responses
        }
        setError(errorDetail);
        setData(null);
        return;
      }

      const json: HealthResponse = await response.json();
      setData(json);
      setError(null);
    } catch (err: unknown) {
      const elapsed = Math.round(performance.now() - start);
      setLatencyMs(elapsed);
      setLastChecked(new Date());
      setData(null);
      if (err instanceof Error) {
        setError(err.message || "Impossibile contattare il server API");
      } else {
        setError("Errore di rete sconosciuto");
      }
    } finally {
      setIsLoading(false);
    }
  }, [apiUrl]);

  useEffect(() => {
    fetchHealth();
  }, [fetchHealth]);

  return {
    data,
    isLoading,
    error,
    latencyMs,
    lastChecked,
    refetch: fetchHealth,
  };
}
