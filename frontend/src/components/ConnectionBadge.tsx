import React from "react";
import { AlertCircle, RefreshCw, Database } from "lucide-react";
import type { UseHealthResult } from "../hooks/useHealth";

interface ConnectionBadgeProps {
  healthState: UseHealthResult;
}

export const ConnectionBadge: React.FC<ConnectionBadgeProps> = ({ healthState }) => {
  const { data, isLoading, error, latencyMs, refetch } = healthState;

  if (isLoading && !data && !error) {
    return (
      <div
        data-testid="connection-loading"
        className="flex items-center gap-2 rounded-full border border-border bg-card/60 px-3 py-1.5 text-xs text-muted-foreground backdrop-blur-sm"
      >
        <RefreshCw className="h-3.5 w-3.5 animate-spin text-primary" />
        <span>Verifica connessione API...</span>
      </div>
    );
  }

  if (error || !data || data.status !== "ok") {
    return (
      <div
        data-testid="connection-error"
        className="flex items-center gap-2 rounded-full border border-destructive/40 bg-destructive/10 px-3 py-1.5 text-xs text-destructive backdrop-blur-sm"
        role="status"
        aria-live="polite"
      >
        <AlertCircle className="h-4 w-4 shrink-0 text-destructive" />
        <span className="font-medium">Backend Disconnesso</span>
        <span className="hidden sm:inline text-destructive/80">({error || "Errore"})</span>
        <button
          onClick={() => refetch()}
          disabled={isLoading}
          aria-label="Riprova connessione"
          className="ml-1 rounded p-0.5 hover:bg-destructive/20 active:scale-95 transition-transform"
        >
          <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
        </button>
      </div>
    );
  }

  return (
    <div
      data-testid="connection-online"
      className="flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1.5 text-xs text-emerald-300 backdrop-blur-sm"
      role="status"
      aria-live="polite"
    >
      <span className="relative flex h-2 w-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-500" />
      </span>

      <span className="font-semibold text-emerald-200">API Online</span>
      <span className="hidden md:inline text-emerald-400/80">v{data.version}</span>

      <span className="hidden sm:inline-flex items-center gap-1 border-l border-emerald-500/20 pl-2 text-emerald-300/90">
        <Database className="h-3 w-3" />
        <span>DB {data.database === "connected" ? "Attivo" : data.database}</span>
      </span>

      {latencyMs !== null && (
        <span className="hidden lg:inline text-emerald-400/60 font-mono text-[10px]">
          {latencyMs}ms
        </span>
      )}

      <button
        onClick={() => refetch()}
        disabled={isLoading}
        title="Ricarica stato connessione"
        aria-label="Ricarica stato connessione"
        className="ml-1 rounded p-0.5 text-emerald-300 hover:bg-emerald-500/20 active:scale-95 transition-transform"
      >
        <RefreshCw className={`h-3 w-3 ${isLoading ? "animate-spin" : ""}`} />
      </button>
    </div>
  );
};
