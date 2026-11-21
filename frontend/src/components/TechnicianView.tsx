import React, { useEffect, useState, useCallback } from "react";
import {
  Wrench,
  RefreshCw,
  FolderOpen,
  Calendar,
  Layers,
  AlertCircle,
  Tag,
  Loader2,
} from "lucide-react";
import type { SupportRequestItem } from "../types/api";
import { getSupportRequests } from "../api/client";

export const TechnicianView: React.FC = () => {
  const [requests, setRequests] = useState<SupportRequestItem[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");

  const loadRequests = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await getSupportRequests(statusFilter, 50, 0);
      setRequests(res.items);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Errore durante il recupero delle richieste IT");
      }
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadRequests();
  }, [loadRequests]);

  return (
    <section
      id="panel-technician"
      role="tabpanel"
      aria-labelledby="tab-technician"
      className="space-y-6"
    >
      {/* Overview & Filter Bar */}
      <div className="flex flex-col gap-4 rounded-2xl border border-border bg-card p-6 shadow-sm md:flex-row md:items-center md:justify-between">
        <div>
          <div className="inline-flex items-center gap-2 rounded-lg bg-accent px-3 py-1 text-xs font-semibold text-accent-foreground">
            <Wrench className="h-3.5 w-3.5" />
            <span>Console Tecnico IT — Richieste Supporto Reali</span>
          </div>
          <h2 className="mt-2 text-xl font-bold text-foreground">
            Elenco Problematiche IT Registrate
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            Visualizzazione dei record SupportRequest salvati su SQLite e collegati alle conversazioni.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <label htmlFor="tech-status-filter" className="text-xs font-medium text-muted-foreground">
            Stato:
          </label>
          <select
            id="tech-status-filter"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-lg border border-input bg-background px-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
          >
            <option value="all">Tutti gli stati</option>
            <option value="open">Aperti (open)</option>
            <option value="in_progress">In corso (in_progress)</option>
            <option value="closed">Chiusi (closed)</option>
          </select>

          <button
            onClick={() => loadRequests()}
            disabled={loading}
            aria-label="Aggiorna lista richieste"
            className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-3 py-1.5 text-xs font-medium text-foreground hover:bg-muted active:scale-95 transition-transform"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Aggiorna</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-xl border border-destructive/40 bg-destructive/10 p-4 text-xs text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {/* Requests Table / Cards */}
      <div className="rounded-2xl border border-border bg-card shadow-sm overflow-hidden">
        {loading && requests.length === 0 ? (
          <div className="flex items-center justify-center p-12 text-xs text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin mr-2 text-primary" />
            <span>Caricamento richieste IT...</span>
          </div>
        ) : requests.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-center text-xs text-muted-foreground">
            <FolderOpen className="h-10 w-10 text-muted-foreground/40 mb-3" />
            <h3 className="text-sm font-semibold text-foreground">Nessuna richiesta registrata</h3>
            <p className="mt-1 max-w-sm">
              Non sono presenti problematiche con i filtri attuali. Le richieste registrate dai
              dipendenti nella Vista Dipendente compariranno qui.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-border bg-muted/40 text-muted-foreground font-semibold">
                  <th className="py-3 px-4">ID Richiesta</th>
                  <th className="py-3 px-4">Titolo & Descrizione</th>
                  <th className="py-3 px-4">Categoria</th>
                  <th className="py-3 px-4">Stato</th>
                  <th className="py-3 px-4">Thread Collegato</th>
                  <th className="py-3 px-4">Data Creazione (UTC)</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {requests.map((req) => (
                  <tr key={req.id} className="hover:bg-muted/20 transition-colors">
                    <td className="py-3 px-4 font-mono font-medium text-foreground">
                      {req.id}
                    </td>
                    <td className="py-3 px-4 max-w-md">
                      <div className="font-semibold text-foreground">{req.title}</div>
                      <div className="truncate text-muted-foreground text-[11px] mt-0.5">
                        {req.description}
                      </div>
                    </td>
                    <td className="py-3 px-4">
                      {req.initial_category ? (
                        <span className="inline-flex items-center gap-1 rounded-md bg-secondary px-2 py-0.5 text-[10px] font-medium text-secondary-foreground">
                          <Tag className="h-3 w-3" />
                          <span>{req.initial_category}</span>
                        </span>
                      ) : (
                        <span className="text-muted-foreground">—</span>
                      )}
                    </td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
                          req.status === "open"
                            ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                            : req.status === "closed"
                            ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                            : "bg-blue-500/10 text-blue-400 border border-blue-500/20"
                        }`}
                      >
                        {req.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-[11px] text-muted-foreground">
                      <span className="inline-flex items-center gap-1">
                        <Layers className="h-3 w-3 text-primary" />
                        <span>{req.conversation_id}</span>
                      </span>
                    </td>
                    <td className="py-3 px-4 text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        <span>
                          {new Date(req.created_at).toLocaleString([], {
                            dateStyle: "short",
                            timeStyle: "short",
                          })}
                        </span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="rounded-xl border border-border/80 bg-background/50 p-4 text-center text-xs text-muted-foreground">
        <span>
          Visualizzazione tabellare minima per <strong>GOAL 02</strong>. Integrazioni ticket esterni
          mock, incident awareness e bozze knowledge base verranno abilitate nelle milestone G05 e G06.
        </span>
      </div>
    </section>
  );
};
