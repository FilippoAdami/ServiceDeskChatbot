import React, { useEffect, useState, useCallback, useMemo } from "react";
import {
  Activity,
  RefreshCw,
  Search,
  ChevronDown,
  ChevronRight,
  User,
  Wrench,
  Server,
  Layers,
  Copy,
  Check,
  Clock,
  Zap,
  AlertTriangle,
  MessageSquare,
  Ticket,
  Maximize2,
  Minimize2,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type {
  AuditCategory,
  AuditConversationSummary,
  AuditEventItem,
} from "../types/api";
import { getAuditConversations, getAuditEvents } from "../api/client";

interface TokenStats {
  prompt_tokens?: number;
  thoughts_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
}

interface AuditPayload {
  tokens?: TokenStats;
  token_usage?: TokenStats;
  latency_ms?: number;
  is_truncated?: boolean;
  finish_reason?: string;
  sources_count?: number;
  sources?: unknown[];
  content?: string;
  description?: string;
  [key: string]: unknown;
}

const CATEGORY_TABS: { id: AuditCategory; label: string; icon: React.FC<{ className?: string }> }[] = [
  { id: "all", label: "Tutti gli Eventi", icon: Layers },
  { id: "employee", label: "Dipendente (Utenti)", icon: User },
  { id: "technician", label: "Tecnico (Operazioni IT)", icon: Wrench },
  { id: "system", label: "Sistema & RAG", icon: Server },
];

export const DebugView: React.FC = () => {
  const [events, setEvents] = useState<AuditEventItem[]>([]);
  const [conversations, setConversations] = useState<AuditConversationSummary[]>([]);
  const [totalEvents, setTotalEvents] = useState<number>(0);
  const [loading, setLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [selectedCategory, setSelectedCategory] = useState<AuditCategory>("all");
  const [selectedConversation, setSelectedConversation] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const fetchAuditData = useCallback(async (isBackground: boolean = false) => {
    if (!isBackground) setIsRefreshing(true);
    try {
      const [eventsRes, convsRes] = await Promise.all([
        getAuditEvents({
          category: selectedCategory !== "all" ? selectedCategory : undefined,
          conversation_id: selectedConversation !== "all" ? selectedConversation : undefined,
          limit: 100,
        }),
        getAuditConversations(100),
      ]);
      setEvents(eventsRes.items);
      setTotalEvents(eventsRes.total);
      setConversations(convsRes.items);
    } catch (err) {
      console.error("Errore recupero log di debug:", err);
    } finally {
      setLoading(false);
      setIsRefreshing(false);
    }
  }, [selectedCategory, selectedConversation]);

  // Initial fetch and on filter change
  useEffect(() => {
    fetchAuditData(false);
  }, [fetchAuditData]);

  // Live Auto-Refresh (3 seconds)
  useEffect(() => {
    if (!autoRefresh) return;
    const interval = setInterval(() => {
      fetchAuditData(true);
    }, 3000);
    return () => clearInterval(interval);
  }, [autoRefresh, fetchAuditData]);

  // Toggle single card expand
  const toggleExpand = (id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  // Expand all / Collapse all
  const expandAll = () => {
    setExpandedIds(new Set(events.map((e) => e.id)));
  };

  const collapseAll = () => {
    setExpandedIds(new Set());
  };

  // Copy JSON payload
  const handleCopyPayload = (id: string, payload: Record<string, unknown>) => {
    navigator.clipboard.writeText(JSON.stringify(payload, null, 2));
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Client-side text filter (searchQuery)
  const filteredEvents = useMemo(() => {
    if (!searchQuery.trim()) return events;
    const q = searchQuery.toLowerCase();
    return events.filter(
      (e) =>
        e.id.toLowerCase().includes(q) ||
        e.event_type.toLowerCase().includes(q) ||
        e.action_label.toLowerCase().includes(q) ||
        (e.conversation_id && e.conversation_id.toLowerCase().includes(q)) ||
        (e.ticket_id && e.ticket_id.toLowerCase().includes(q)) ||
        JSON.stringify(e.payload).toLowerCase().includes(q)
    );
  }, [events, searchQuery]);

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case "employee":
        return "bg-sky-500/10 text-sky-400 border-sky-500/30";
      case "technician":
        return "bg-purple-500/10 text-purple-400 border-purple-500/30";
      default:
        return "bg-slate-500/10 text-slate-400 border-slate-500/30";
    }
  };

  return (
    <div className="flex flex-col gap-6 w-full max-w-7xl mx-auto pb-12">
      {/* Top Header Card */}
      <div className="rounded-2xl border border-border bg-card/80 p-6 shadow-sm backdrop-blur-md">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                <Activity className="h-5 w-5" />
              </div>
              <h1 className="text-2xl font-bold tracking-tight text-foreground">
                Console Live Debug & Audit Eventi
              </h1>
            </div>
            <p className="text-sm text-muted-foreground">
              Monitoraggio trasparente in tempo reale del ciclo di vita: sessioni utente, operazioni del tecnico,
              ragionamento AI, metriche token e audit trail.
            </p>
          </div>

          {/* Controls: Live auto-refresh toggle & refresh button */}
          <div className="flex items-center gap-3">
            <button
              onClick={() => setAutoRefresh((v) => !v)}
              className={`flex items-center gap-2 rounded-xl px-3.5 py-2 text-xs font-semibold border transition-all ${
                autoRefresh
                  ? "bg-emerald-500/10 border-emerald-500/40 text-emerald-400 shadow-sm"
                  : "bg-muted/50 border-border text-muted-foreground hover:bg-muted"
              }`}
            >
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  autoRefresh ? "bg-emerald-500 animate-pulse" : "bg-muted-foreground"
                }`}
              />
              {autoRefresh ? "Live Attivo (3s)" : "Live In Pausa"}
            </button>

            <button
              onClick={() => fetchAuditData(false)}
              disabled={isRefreshing}
              className="flex items-center gap-2 rounded-xl border border-border bg-card px-3.5 py-2 text-xs font-medium text-foreground hover:bg-accent transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${isRefreshing ? "animate-spin text-primary" : ""}`} />
              Aggiorna ora
            </button>
          </div>
        </div>

        {/* Filter Bar */}
        <div className="mt-6 flex flex-col md:flex-row items-stretch md:items-center justify-between gap-4 border-t border-border/60 pt-5">
          {/* Category Tabs */}
          <div className="flex flex-wrap gap-1.5 p-1 bg-muted/30 border border-border/50 rounded-xl">
            {CATEGORY_TABS.map((tab) => {
              const Icon = tab.icon;
              const isActive = selectedCategory === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setSelectedCategory(tab.id)}
                  className={`flex items-center gap-2 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
                    isActive
                      ? "bg-primary text-primary-foreground font-semibold shadow-sm"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted/50"
                  }`}
                >
                  <Icon className="h-3.5 w-3.5" />
                  {tab.label}
                </button>
              );
            })}
          </div>

          {/* Chat selector dropdown & Search box */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Conversation Thread Selector */}
            <div className="flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-muted-foreground" />
              <select
                value={selectedConversation}
                onChange={(e) => setSelectedConversation(e.target.value)}
                className="rounded-xl border border-border bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-primary max-w-xs"
              >
                <option value="all">Tutte le chat ({conversations.length})</option>
                {conversations.map((c) => (
                  <option key={c.conversation_id} value={c.conversation_id}>
                    {c.title.length > 28 ? `${c.title.slice(0, 28)}...` : c.title} ({c.event_count} ev)
                  </option>
                ))}
              </select>
            </div>

            {/* Keyword Search Input */}
            <div className="relative">
              <Search className="absolute left-3 top-2 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Cerca evento, ID o payload..."
                className="rounded-xl border border-border bg-background pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-primary w-48 sm:w-60"
              />
            </div>
          </div>
        </div>

        {/* Status Counter & Bulk expand/collapse */}
        <div className="mt-4 flex items-center justify-between text-xs text-muted-foreground pt-3 border-t border-border/30">
          <div>
            Mostrati <span className="font-semibold text-foreground">{filteredEvents.length}</span> di{" "}
            <span className="font-semibold text-foreground">{totalEvents}</span> eventi registrati
            {selectedConversation !== "all" && " (per chat selezionata)"}
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={expandAll}
              className="flex items-center gap-1 hover:text-foreground transition-colors"
            >
              <Maximize2 className="h-3 w-3" />
              Espandi tutti
            </button>
            <span className="text-border">|</span>
            <button
              onClick={collapseAll}
              className="flex items-center gap-1 hover:text-foreground transition-colors"
            >
              <Minimize2 className="h-3 w-3" />
              Collassa tutti
            </button>
          </div>
        </div>
      </div>

      {/* Events Feed */}
      <div className="space-y-3">
        {loading && events.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-border bg-card/40">
            <RefreshCw className="h-8 w-8 animate-spin text-primary mb-3" />
            <p className="text-sm font-medium text-foreground">Caricamento log di audit in corso...</p>
          </div>
        ) : filteredEvents.length === 0 ? (
          <div className="flex flex-col items-center justify-center p-12 text-center rounded-2xl border border-dashed border-border bg-card/20">
            <Activity className="h-8 w-8 text-muted-foreground mb-3 opacity-50" />
            <p className="text-sm font-medium text-foreground">Nessun evento registrato per i filtri selezionati</p>
            <p className="text-xs text-muted-foreground mt-1">
              Prova a selezionare &quot;Tutti gli Eventi&quot; o a pulire la barra di ricerca.
            </p>
          </div>
        ) : (
          filteredEvents.map((event) => {
            const isExpanded = expandedIds.has(event.id);
            const payload = (event.payload || {}) as AuditPayload;
            const tokens = payload.tokens || payload.token_usage;
            const latency = payload.latency_ms;
            const isTruncated = Boolean(payload.is_truncated);
            const finishReason = payload.finish_reason;
            const sourcesList = Array.isArray(payload.sources) ? payload.sources : [];
            const sourcesCount = payload.sources_count || sourcesList.length;

            return (
              <div
                key={event.id}
                className="rounded-xl border border-border bg-card/90 shadow-sm transition-all hover:border-border/80 overflow-hidden"
              >
                {/* Collapsible Header Row */}
                <div
                  onClick={() => toggleExpand(event.id)}
                  className="flex flex-wrap items-center justify-between gap-3 px-4 py-3 cursor-pointer select-none bg-card hover:bg-accent/40 transition-colors"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <button
                      type="button"
                      aria-label="Toggle details"
                      className="text-muted-foreground hover:text-foreground p-0.5 rounded"
                    >
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                    </button>

                    {/* Category Badge */}
                    <span
                      className={`inline-flex items-center rounded-md border px-2 py-0.5 text-[11px] font-semibold tracking-wide uppercase ${getCategoryBadge(
                        event.category
                      )}`}
                    >
                      {event.category === "employee"
                        ? "Dipendente"
                        : event.category === "technician"
                        ? "Tecnico"
                        : "Sistema"}
                    </span>

                    {/* Action Label */}
                    <div className="flex items-baseline gap-2 truncate flex-1 min-w-0">
                      <span className="text-sm font-semibold text-foreground truncate">
                        {event.action_label}
                      </span>
                      <span className="text-xs font-mono text-muted-foreground hidden sm:inline shrink-0">
                        ({event.event_type})
                      </span>
                      {(payload.content || payload.description) && (
                        <span className="text-xs text-muted-foreground truncate hidden md:inline font-sans italic opacity-85">
                          — "{String(payload.content || payload.description).slice(0, 65)}
                          {String(payload.content || payload.description).length > 65 ? "..." : ""}"
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Right Header Badges */}
                  <div className="flex items-center gap-2.5 text-xs">
                    {/* Token Badge */}
                    {tokens && (
                      <span className="hidden md:inline-flex items-center gap-1 rounded-md bg-primary/10 border border-primary/20 px-2 py-0.5 text-[11px] font-medium text-primary">
                        <Zap className="h-3 w-3" />
                        {tokens.total_tokens || tokens.completion_tokens || 0} tok
                      </span>
                    )}

                    {/* Latency Badge */}
                    {latency !== undefined && latency !== null && (
                      <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-medium text-muted-foreground">
                        <Clock className="h-3 w-3" />
                        {latency} ms
                      </span>
                    )}

                    {/* Truncated Warning */}
                    {isTruncated && (
                      <span className="inline-flex items-center gap-1 rounded-md bg-amber-500/10 border border-amber-500/30 px-2 py-0.5 text-[11px] font-semibold text-amber-400">
                        <AlertTriangle className="h-3 w-3" />
                        Troncato
                      </span>
                    )}

                    {/* Thread or Ticket Link */}
                    {event.conversation_id && (
                      <span className="hidden lg:inline-flex items-center gap-1 rounded bg-muted/60 px-1.5 py-0.5 font-mono text-[11px] text-muted-foreground">
                        <MessageSquare className="h-3 w-3" />
                        {event.conversation_id.slice(0, 10)}...
                      </span>
                    )}

                    {event.ticket_id && (
                      <span className="inline-flex items-center gap-1 rounded bg-amber-500/10 border border-amber-500/20 px-1.5 py-0.5 font-mono text-[11px] text-amber-400">
                        <Ticket className="h-3 w-3" />
                        {event.ticket_id.slice(0, 9)}
                      </span>
                    )}

                    {/* Timestamp */}
                    <span className="font-mono text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(event.created_at).toLocaleTimeString("it-IT", {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                  </div>
                </div>

                {/* Expanded Details Body */}
                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: "auto", opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="border-t border-border/60 bg-muted/20 px-4 py-4"
                    >
                      {/* LLM Metrics Summary (if available) */}
                      {tokens && (
                        <div className="mb-4 grid grid-cols-2 sm:grid-cols-4 gap-3 p-3 rounded-xl bg-card/60 border border-border">
                          <div>
                            <span className="text-[11px] text-muted-foreground uppercase tracking-wider block">
                              Prompt Tokens
                            </span>
                            <span className="text-sm font-semibold text-foreground font-mono">
                              {tokens.prompt_tokens || 0}
                            </span>
                          </div>
                          <div>
                            <span className="text-[11px] text-muted-foreground uppercase tracking-wider block">
                              Thinking / Reasoning
                            </span>
                            <span className="text-sm font-semibold text-purple-400 font-mono">
                              {tokens.thoughts_tokens || 0}
                            </span>
                          </div>
                          <div>
                            <span className="text-[11px] text-muted-foreground uppercase tracking-wider block">
                              Completion Tokens
                            </span>
                            <span className="text-sm font-semibold text-emerald-400 font-mono">
                              {tokens.completion_tokens || 0}
                            </span>
                          </div>
                          <div>
                            <span className="text-[11px] text-muted-foreground uppercase tracking-wider block">
                              Totale Token / Finish
                            </span>
                            <span className="text-sm font-semibold text-foreground font-mono">
                              {tokens.total_tokens || 0}{" "}
                              {finishReason && (
                                <span className="text-xs text-muted-foreground font-normal">
                                  ({finishReason})
                                </span>
                              )}
                            </span>
                          </div>
                        </div>
                      )}

                      {/* Message Content / Description Preview */}
                      {(payload.content || payload.description) && (
                        <div className="mb-4 p-3.5 rounded-xl bg-card/80 border border-primary/20 shadow-sm">
                          <span className="text-[11px] font-semibold text-primary uppercase tracking-wider block mb-1.5">
                            Contenuto Messaggio (Sanitizzato)
                          </span>
                          <p className="text-xs text-foreground whitespace-pre-wrap font-sans leading-relaxed">
                            {String(payload.content || payload.description)}
                          </p>
                        </div>
                      )}

                      {/* Associated IDs and Metadata */}
                      <div className="mb-3 flex flex-wrap items-center gap-4 text-xs text-muted-foreground">
                        <div>
                          <strong className="text-foreground">Event ID:</strong>{" "}
                          <span className="font-mono">{event.id}</span>
                        </div>
                        {event.conversation_id && (
                          <div>
                            <strong className="text-foreground">Conversazione:</strong>{" "}
                            <span className="font-mono">{event.conversation_id}</span>
                          </div>
                        )}
                        {event.request_id && (
                          <div>
                            <strong className="text-foreground">Richiesta ID:</strong>{" "}
                            <span className="font-mono">{event.request_id}</span>
                          </div>
                        )}
                        {event.ticket_id && (
                          <div>
                            <strong className="text-foreground">Ticket ID:</strong>{" "}
                            <span className="font-mono">{event.ticket_id}</span>
                          </div>
                        )}
                        {sourcesCount > 0 && (
                          <div>
                            <strong className="text-foreground">Fonti KB:</strong>{" "}
                            <span>{sourcesCount} consultate</span>
                          </div>
                        )}
                      </div>

                      {/* Payload JSON Viewer */}
                      <div className="relative mt-2">
                        <div className="flex items-center justify-between pb-1.5">
                          <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Payload Audit Completo (JSON)
                          </span>
                          <button
                            onClick={() => handleCopyPayload(event.id, payload)}
                            className="flex items-center gap-1 text-[11px] text-muted-foreground hover:text-foreground transition-colors px-2 py-0.5 rounded bg-card border border-border"
                          >
                            {copiedId === event.id ? (
                              <>
                                <Check className="h-3 w-3 text-emerald-400" />
                                <span className="text-emerald-400">Copiato!</span>
                              </>
                            ) : (
                              <>
                                <Copy className="h-3 w-3" />
                                <span>Copia JSON</span>
                              </>
                            )}
                          </button>
                        </div>
                        <pre className="p-3 rounded-lg bg-background/90 border border-border font-mono text-xs text-foreground/90 overflow-x-auto max-h-72 select-text">
                          {JSON.stringify(payload, null, 2)}
                        </pre>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
