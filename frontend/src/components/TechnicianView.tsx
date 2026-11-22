import React, { useEffect, useState, useCallback } from "react";
import {
  Wrench,
  RefreshCw,
  FolderOpen,
  AlertCircle,
  Tag,
  Loader2,
  Ticket as TicketIcon,
  CheckCircle2,
  Clock,
  ArrowRight,
  FileText,
  Radio,
  BookOpen,
  Send,
  Sparkles,
} from "lucide-react";
import {
  type IncidentItem,
  type SupportRequestItem,
  type TicketDetail,
  type TicketItem,
  TASK_CATEGORIES,
} from "../types/api";
import {
  addTicketNote,
  generateKnowledgeProposal,
  getIncidents,
  getSupportRequests,
  getTicket,
  getTickets,
  linkTicketIncident,
  updateTicketStatus,
} from "../api/client";
import { TechnicianChatPanel } from "./TechnicianChatPanel";
import { KnowledgeProposalsPanel } from "./KnowledgeProposalsPanel";

const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  open: ["in_progress", "closed"],
  in_progress: ["resolved", "open", "closed"],
  resolved: ["in_progress", "closed"],
  closed: ["open"],
};

const STATUS_CONFIG: Record<string, { label: string; badge: string; border: string; dot: string }> = {
  open: {
    label: "Aperto",
    badge: "bg-amber-500/15 text-amber-300 border-amber-500/40",
    border: "border-l-amber-500",
    dot: "bg-amber-400",
  },
  in_progress: {
    label: "In lavorazione",
    badge: "bg-blue-500/15 text-blue-300 border-blue-500/40",
    border: "border-l-blue-500",
    dot: "bg-blue-400",
  },
  resolved: {
    label: "Risolto",
    badge: "bg-emerald-500/15 text-emerald-300 border-emerald-500/40",
    border: "border-l-emerald-500",
    dot: "bg-emerald-400",
  },
  closed: {
    label: "Chiuso",
    badge: "bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-sm shadow-rose-950/40",
    border: "border-l-rose-500",
    dot: "bg-rose-500",
  },
};

const PRIORITY_CONFIG: Record<string, { label: string; badge: string }> = {
  low: { label: "Bassa", badge: "text-slate-400 bg-slate-500/10 border-slate-500/20" },
  medium: { label: "Media", badge: "text-blue-400 bg-blue-500/10 border-blue-500/20" },
  high: { label: "Alta", badge: "text-amber-400 bg-amber-500/10 border-amber-500/20" },
  critical: { label: "Critica", badge: "text-rose-400 bg-rose-500/10 border-rose-500/20" },
};

const INCIDENT_STATUS_CONFIG: Record<string, { label: string; badge: string }> = {
  investigating: { label: "Indagine in corso", badge: "bg-amber-500/15 text-amber-300 border-amber-500/30" },
  identified: { label: "Identificato", badge: "bg-purple-500/15 text-purple-300 border-purple-500/30" },
  monitoring: { label: "Monitoraggio", badge: "bg-blue-500/15 text-blue-300 border-blue-500/30" },
  resolved: { label: "Risolto", badge: "bg-emerald-500/15 text-emerald-300 border-emerald-500/30" },
};

export const TechnicianView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"tickets" | "incidents" | "requests" | "kb_proposals">("tickets");

  // Tickets State
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [ticketDetail, setTicketDetail] = useState<TicketDetail | null>(null);
  const [ticketsLoading, setTicketsLoading] = useState<boolean>(true);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [ticketStatusFilter, setTicketStatusFilter] = useState<string>("all");
  const [ticketCategoryFilter, setTicketCategoryFilter] = useState<string>("all");
  const [ticketError, setTicketError] = useState<string | null>(null);

  // Knowledge Proposal Generation State
  const [generatingKB, setGeneratingKB] = useState<boolean>(false);
  const [kbNotification, setKbNotification] = useState<{ id: string; title: string } | null>(null);

  // Note & Status Form State
  const [noteContent, setNoteContent] = useState<string>("");
  const [submittingNote, setSubmittingNote] = useState<boolean>(false);
  const [transitioning, setTransitioning] = useState<boolean>(false);
  const [statusNoteText, setStatusNoteText] = useState<string>("");
  const [pendingStatus, setPendingStatus] = useState<string | null>(null);

  // Incidents State
  const [incidents, setIncidents] = useState<IncidentItem[]>([]);
  const [incidentsLoading, setIncidentsLoading] = useState<boolean>(false);
  const [incidentLinkSelect, setIncidentLinkSelect] = useState<string>("");

  // Support Requests State
  const [requests, setRequests] = useState<SupportRequestItem[]>([]);
  const [requestsLoading, setRequestsLoading] = useState<boolean>(false);
  const [requestStatusFilter, setRequestStatusFilter] = useState<string>("all");

  // Load Tickets
  const loadTickets = useCallback(async (selectId?: string) => {
    try {
      setTicketsLoading(true);
      setTicketError(null);
      const res = await getTickets(ticketStatusFilter, ticketCategoryFilter);
      const items = Array.isArray(res?.items) ? res.items : [];
      setTickets(items);

      const targetId = selectId || (items.length > 0 ? (selectedTicketId && items.some(t => t.id === selectedTicketId) ? selectedTicketId : items[0].id) : null);
      setSelectedTicketId(targetId);

      if (targetId) {
        const detail = await getTicket(targetId);
        setTicketDetail(detail);
        setIncidentLinkSelect(detail?.incident_id || "");
      } else {
        setTicketDetail(null);
      }
    } catch (err: unknown) {
      setTicketError(err instanceof Error ? err.message : "Errore recupero ticket");
    } finally {
      setTicketsLoading(false);
    }
  }, [ticketStatusFilter, ticketCategoryFilter, selectedTicketId]);

  // Load Single Ticket Detail
  const selectTicket = async (id: string) => {
    try {
      setSelectedTicketId(id);
      setDetailLoading(true);
      setTicketError(null);
      const detail = await getTicket(id);
      setTicketDetail(detail);
      setIncidentLinkSelect(detail?.incident_id || "");
      setPendingStatus(null);
      setStatusNoteText("");
    } catch (err: unknown) {
      setTicketError(err instanceof Error ? err.message : "Errore caricamento dettaglio ticket");
    } finally {
      setDetailLoading(false);
    }
  };

  // Load Incidents
  const loadIncidents = useCallback(async () => {
    try {
      setIncidentsLoading(true);
      const res = await getIncidents();
      setIncidents(Array.isArray(res?.items) ? res.items : []);
    } catch (err: unknown) {
      setTicketError(err instanceof Error ? err.message : "Errore recupero incidenti");
    } finally {
      setIncidentsLoading(false);
    }
  }, []);

  // Load Support Requests
  const loadRequests = useCallback(async () => {
    try {
      setRequestsLoading(true);
      const res = await getSupportRequests(requestStatusFilter, 50, 0);
      setRequests(Array.isArray(res?.items) ? res.items : []);
    } catch (err: unknown) {
      setTicketError(err instanceof Error ? err.message : "Errore recupero richieste IT");
    } finally {
      setRequestsLoading(false);
    }
  }, [requestStatusFilter]);

  // Initial and reactive effects
  useEffect(() => {
    loadTickets();
    loadIncidents();
  }, [loadTickets, loadIncidents]);

  useEffect(() => {
    if (activeTab === "requests") {
      loadRequests();
    }
  }, [activeTab, loadRequests]);

  // Handle Note Submission
  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicketId || !noteContent.trim() || submittingNote) return;

    try {
      setSubmittingNote(true);
      setTicketError(null);
      await addTicketNote(selectedTicketId, noteContent.trim(), "technician_demo");
      setNoteContent("");
      // Refresh ticket detail to include new activity
      const updated = await getTicket(selectedTicketId);
      setTicketDetail(updated);
    } catch (err: unknown) {
      setTicketError(err instanceof Error ? err.message : "Errore inserimento nota");
    } finally {
      setSubmittingNote(false);
    }
  };

  // Handle State Transition
  const handleApplyStatusTransition = async (newStatus: string) => {
    if (!selectedTicketId || transitioning) return;
    try {
      setTransitioning(true);
      setTicketError(null);
      const updated = await updateTicketStatus(
        selectedTicketId,
        newStatus,
        statusNoteText.trim() || undefined,
        "technician_demo"
      );
      setTicketDetail(updated);
      setPendingStatus(null);
      setStatusNoteText("");
      // Refresh tickets list to reflect updated status
      loadTickets(selectedTicketId);
    } catch (err: unknown) {
      setTicketError(err instanceof Error ? err.message : "Transizione non valida");
    } finally {
      setTransitioning(false);
    }
  };

  // Handle Incident Link / Unlink
  const handleUpdateIncidentLink = async () => {
    if (!selectedTicketId) return;
    try {
      setTicketError(null);
      const targetIncId = incidentLinkSelect || null;
      const updated = await linkTicketIncident(selectedTicketId, targetIncId, "technician_demo");
      setTicketDetail(updated);
      loadTickets(selectedTicketId);
      loadIncidents();
    } catch (err: unknown) {
      setTicketError(err instanceof Error ? err.message : "Errore aggiornamento collegamento incidente");
    }
  };

  // Handle KB Proposal Generation from Ticket
  const handleGenerateTicketKBProposal = async () => {
    if (!selectedTicketId) return;
    try {
      setGeneratingKB(true);
      setTicketError(null);
      const proposal = await generateKnowledgeProposal("ticket", selectedTicketId, "technician_demo");
      setKbNotification({ id: proposal.id, title: proposal.title });
    } catch (err: unknown) {
      setTicketError(err instanceof Error ? err.message : "Errore generazione bozza KB da ticket");
    } finally {
      setGeneratingKB(false);
    }
  };

  // Handle Applying Operational Proposal from AI Copilot to Ticket
  const handleApplyAssistantProposal = async (
    proposedStatus?: string | null,
    proposedNote?: string | null
  ) => {
    if (!selectedTicketId) return;
    try {
      setTicketError(null);
      const targetStatus = proposedStatus || (ticketDetail ? ticketDetail.status : "in_progress");
      const updated = await updateTicketStatus(
        selectedTicketId,
        targetStatus,
        proposedNote || undefined,
        "technician_demo"
      );
      setTicketDetail(updated);
      loadTickets(selectedTicketId);
    } catch (err: unknown) {
      setTicketError(err instanceof Error ? err.message : "Errore applicazione proposta assistente");
    }
  };

  // Handle KB Proposal Generation from Support Request
  const handleGenerateRequestKBProposal = async (requestId: string) => {
    try {
      setTicketError(null);
      const proposal = await generateKnowledgeProposal("support_request", requestId, "technician_demo");
      setKbNotification({ id: proposal.id, title: proposal.title });
      setActiveTab("kb_proposals");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Errore generazione bozza KB");
    }
  };

  return (
    <section
      id="panel-technician"
      role="tabpanel"
      aria-labelledby="tab-technician"
      className="flex flex-col h-full min-h-0 space-y-4"
    >
      {/* Top Header & Sub-Navigation */}
      <div className="shrink-0 flex flex-col gap-4 rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-4 shadow-xl md:flex-row md:items-center md:justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-accent-foreground shadow-md">
            <Wrench className="h-5 w-5" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-foreground">Console Tecnico IT — Richieste Supporto Reali</h2>
              <span className="rounded-full bg-primary/20 px-2 py-0.5 text-[10px] font-semibold text-primary">
                Local-first Demo
              </span>
            </div>
            <p className="text-xs text-muted-foreground">
              Gestione escalation, diagnosi e coordinamento incidenti aziendali
            </p>
          </div>
        </div>

        {/* Sub-tabs & Refresh */}
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-xl bg-background/80 p-1 border border-white/10 shadow-inner">
            <button
              onClick={() => setActiveTab("tickets")}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                activeTab === "tickets"
                  ? "bg-primary text-primary-foreground shadow"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <TicketIcon className="h-3.5 w-3.5" />
              <span>Ticket Service Desk</span>
              {(tickets ?? []).length > 0 && (
                <span className="ml-1 rounded-full bg-white/20 px-1.5 py-0.2 text-[10px]">
                  {(tickets ?? []).length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("incidents")}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                activeTab === "incidents"
                  ? "bg-primary text-primary-foreground shadow"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <Radio className="h-3.5 w-3.5" />
              <span>Incidenti Noti</span>
              {(incidents ?? []).length > 0 && (
                <span className="ml-1 rounded-full bg-white/20 px-1.5 py-0.2 text-[10px]">
                  {(incidents ?? []).length}
                </span>
              )}
            </button>

            <button
              onClick={() => setActiveTab("requests")}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                activeTab === "requests"
                  ? "bg-primary text-primary-foreground shadow"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <FolderOpen className="h-3.5 w-3.5" />
              <span>Tutte le Richieste</span>
            </button>

            <button
              onClick={() => setActiveTab("kb_proposals")}
              className={`flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-semibold transition-all ${
                activeTab === "kb_proposals"
                  ? "bg-primary text-primary-foreground shadow"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              <BookOpen className="h-3.5 w-3.5" />
              <span>Proposte Articoli KB</span>
            </button>
          </div>

          <button
            onClick={() => {
              if (activeTab === "tickets") loadTickets();
              else if (activeTab === "incidents") loadIncidents();
              else loadRequests();
            }}
            disabled={ticketsLoading || incidentsLoading || requestsLoading}
            aria-label="Aggiorna lista"
            className="inline-flex items-center gap-1.5 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-medium text-foreground hover:bg-white/[0.08] active:scale-95 transition-transform"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 ${
                ticketsLoading || incidentsLoading || requestsLoading ? "animate-spin" : ""
              }`}
            />
            <span className="hidden sm:inline">Aggiorna</span>
          </button>
        </div>
      </div>

      {ticketError && (
        <div className="shrink-0 flex items-center gap-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>{ticketError}</span>
        </div>
      )}

      {/* TAB 1: TICKETS MASTER-DETAIL */}
      {activeTab === "tickets" && (
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-4 overflow-hidden">
          {/* Master List Column (5 cols) */}
          <div className="lg:col-span-5 flex flex-col h-full min-h-0 rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-4 shadow-xl overflow-hidden">
            {/* Filter Pills Bar */}
            <div className="shrink-0 pb-3 border-b border-white/10 space-y-2.5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-semibold text-foreground">Stato:</span>
                <div className="flex flex-wrap gap-1">
                  {(["all", "open", "in_progress", "resolved", "closed"] as const).map((st) => (
                    <button
                      key={st}
                      onClick={() => setTicketStatusFilter(st)}
                      className={`rounded-lg px-2 py-1 text-[11px] font-semibold transition-all ${
                        ticketStatusFilter === st
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "bg-white/[0.04] text-muted-foreground hover:bg-white/[0.08]"
                      }`}
                    >
                      {st === "all" ? "Tutti" : STATUS_CONFIG[st]?.label || st}
                    </button>
                  ))}
                </div>
              </div>

              {/* Category Filter Pills */}
              <div className="flex flex-col gap-1.5 pt-2 border-t border-white/5">
                <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                  Categoria:
                </span>
                <div className="flex flex-wrap gap-1">
                  <button
                    onClick={() => setTicketCategoryFilter("all")}
                    className={`rounded-lg px-2 py-0.5 text-[11px] font-semibold transition-all ${
                      ticketCategoryFilter === "all"
                        ? "bg-primary text-primary-foreground shadow-sm"
                        : "bg-white/[0.04] text-muted-foreground hover:bg-white/[0.08]"
                    }`}
                  >
                    Tutte
                  </button>
                  {TASK_CATEGORIES.map((cat) => (
                    <button
                      key={cat}
                      onClick={() => setTicketCategoryFilter(cat)}
                      className={`rounded-lg px-2 py-0.5 text-[11px] font-semibold transition-all ${
                        ticketCategoryFilter === cat
                          ? "bg-primary text-primary-foreground shadow-sm"
                          : "bg-white/[0.04] text-muted-foreground hover:bg-white/[0.08]"
                      }`}
                    >
                      {cat}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Ticket Cards List */}
            <div className="mt-3 flex-1 min-h-0 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
              {ticketsLoading && (tickets ?? []).length === 0 ? (
                <div className="flex items-center justify-center p-8 text-xs text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin mr-2 text-primary" />
                  <span>Caricamento ticket...</span>
                </div>
              ) : (tickets ?? []).length === 0 ? (
                <div className="rounded-xl border border-dashed border-white/10 p-8 text-center text-xs text-muted-foreground">
                  <TicketIcon className="h-8 w-8 text-muted-foreground/30 mx-auto mb-2" />
                  <p className="font-semibold text-foreground">Nessun ticket presente</p>
                  <p className="mt-1">
                    I ticket vengono generati automaticamente all&apos;escalation dal chatbot.
                  </p>
                </div>
              ) : (
                (tickets ?? []).map((t) => {
                  const isSelected = t.id === selectedTicketId;
                  const statusConf = STATUS_CONFIG[t.status] || { label: t.status, badge: "bg-muted" };
                  const priorityConf = PRIORITY_CONFIG[t.priority] || { label: t.priority, badge: "bg-muted" };

                  return (
                    <button
                      key={t.id}
                      onClick={() => selectTicket(t.id)}
                      className={`w-full text-left rounded-xl p-3 text-xs transition-all border border-l-4 ${statusConf.border} ${
                        isSelected
                          ? "border-primary bg-primary/15 shadow-md backdrop-blur-md"
                          : "border-white/5 bg-white/[0.03] hover:bg-white/[0.07] hover:border-white/10"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2">
                        <div className="flex items-center gap-1.5">
                          <span className="font-mono font-bold text-foreground">{t.id}</span>
                          <span
                            className={`inline-flex items-center gap-1 rounded border px-1.5 py-0.2 text-[10px] font-semibold uppercase ${statusConf.badge}`}
                          >
                            <span className={`h-1.5 w-1.5 rounded-full ${statusConf.dot}`} />
                            {statusConf.label}
                          </span>
                        </div>
                        <span
                          className={`rounded border px-1.5 py-0.2 text-[10px] font-semibold ${priorityConf.badge}`}
                        >
                          {priorityConf.label}
                        </span>
                      </div>

                      <div className="mt-1.5 flex items-center justify-between gap-2">
                        <span className="font-semibold text-foreground truncate">{t.title}</span>
                        {t.category && (
                          <span className="shrink-0 rounded bg-white/10 border border-white/10 px-1.5 py-0.2 text-[10px] text-muted-foreground font-medium">
                            {t.category}
                          </span>
                        )}
                      </div>
                      <p className="mt-0.5 text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                        {t.summary}
                      </p>

                      <div className="mt-2.5 flex items-center justify-between text-[10px] text-muted-foreground border-t border-white/5 pt-1.5">
                        <div className="flex items-center gap-1.5">
                          {t.incident_id && (
                            <span className="inline-flex items-center gap-1 rounded bg-amber-500/15 text-amber-300 px-1.5 py-0.2 font-mono">
                              <Radio className="h-2.5 w-2.5" />
                              {t.incident_id}
                            </span>
                          )}
                          <span className="rounded bg-white/5 px-1 py-0.2 text-[9px] uppercase font-medium">
                            {t.summary_quality === "llm" ? "Diagnosi LLM" : "Fallback"}
                          </span>
                        </div>
                        <span className="flex items-center gap-1">
                          <Clock className="h-3 w-3" />
                          {new Date(t.updated_at).toLocaleTimeString([], {
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </span>
                      </div>
                    </button>
                  );
                })
              )}
            </div>
          </div>

          {/* Detail Pane Column (7 cols) */}
          <div className="lg:col-span-7 flex flex-col h-full min-h-0 rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-5 shadow-xl overflow-hidden">
            {detailLoading ? (
              <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mr-2 text-primary" />
                <span>Caricamento dettagli ticket...</span>
              </div>
            ) : !ticketDetail ? (
              <div className="flex h-full flex-col items-center justify-center text-center p-8 text-xs text-muted-foreground">
                <FileText className="h-10 w-10 text-muted-foreground/30 mb-2" />
                <h3 className="text-sm font-semibold text-foreground">Nessun ticket selezionato</h3>
                <p className="mt-1 max-w-sm">
                  Seleziona un ticket dall&apos;elenco a sinistra per visualizzare i rilievi diagnostici,
                  aggiornare lo stato operativo e inserire note tecniche.
                </p>
              </div>
            ) : (
              <div className="flex-1 min-h-0 overflow-y-auto space-y-4 pr-1 custom-scrollbar">
                {/* Detail Header */}
                <div className="flex flex-col gap-2 pb-4 border-b border-white/10">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <code className="text-sm font-mono font-bold text-primary bg-primary/10 border border-primary/20 px-2.5 py-1 rounded-lg">
                        {ticketDetail.id}
                      </code>
                      <span
                        className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
                          STATUS_CONFIG[ticketDetail.status]?.badge || "bg-muted"
                        }`}
                      >
                        <span
                          className={`h-1.5 w-1.5 rounded-full ${
                            STATUS_CONFIG[ticketDetail.status]?.dot || "bg-muted-foreground"
                          }`}
                        />
                        {STATUS_CONFIG[ticketDetail.status]?.label || ticketDetail.status}
                      </span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                          PRIORITY_CONFIG[ticketDetail.priority]?.badge || "bg-muted"
                        }`}
                      >
                        Priorità {PRIORITY_CONFIG[ticketDetail.priority]?.label || ticketDetail.priority}
                      </span>
                      {ticketDetail.category && (
                        <span className="rounded-full border border-white/20 bg-white/10 px-2.5 py-0.5 text-[10px] font-semibold text-foreground">
                          {ticketDetail.category}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2">
                      <span className="rounded-lg bg-white/5 border border-white/10 px-2 py-0.5 text-[10px] text-muted-foreground">
                        Origine: <strong>{ticketDetail.summary_quality === "llm" ? "Sintesi AI Gemini" : "Fallback Deterministico"}</strong>
                      </span>
                      <button
                        onClick={handleGenerateTicketKBProposal}
                        disabled={generatingKB}
                        className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary hover:bg-primary/20 transition-all disabled:opacity-50"
                        title="Genera una bozza di articolo per la Knowledge Base da questo ticket"
                      >
                        {generatingKB ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <BookOpen className="h-3 w-3" />
                        )}
                        <span>Genera Bozza KB</span>
                      </button>
                    </div>
                  </div>

                  <h3 className="text-base font-bold text-foreground mt-1">{ticketDetail.title}</h3>

                  <div className="flex flex-wrap gap-3 text-[11px] text-muted-foreground mt-0.5">
                    <span>
                      Richiesta: <code className="font-mono text-foreground">{ticketDetail.support_request_id}</code>
                    </span>
                    <span>
                      Thread: <code className="font-mono text-foreground">{ticketDetail.conversation_id}</code>
                    </span>
                    <span>
                      Data: {new Date(ticketDetail.created_at).toLocaleString()}
                    </span>
                  </div>
                </div>

                {/* KB Notification Banner if generated */}
                {kbNotification && (
                  <div className="rounded-xl border border-primary/30 bg-primary/10 p-3 text-xs text-foreground flex items-center justify-between gap-2 shadow-sm">
                    <div className="flex items-center gap-2">
                      <BookOpen className="h-4 w-4 text-primary shrink-0" />
                      <span>
                        Bozza articolo KB creata: <strong>{kbNotification.title}</strong> (<code>{kbNotification.id}</code>)
                      </span>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setActiveTab("kb_proposals")}
                        className="rounded-lg bg-primary px-2.5 py-1 text-[11px] font-bold text-primary-foreground hover:bg-primary-hover shadow"
                      >
                        Revisiona Bozza
                      </button>
                      <button
                        onClick={() => setKbNotification(null)}
                        className="text-xs text-muted-foreground hover:text-foreground"
                      >
                        Chiudi
                      </button>
                    </div>
                  </div>
                )}

                {/* Operations & Transitions Control Panel */}
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-3">
                  <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                    {/* Status Transitions */}
                    <div>
                      <div className="text-[11px] font-semibold text-foreground uppercase tracking-wider mb-1.5">
                        Transizione Stato Operativo
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5">
                        {(ALLOWED_TRANSITIONS[ticketDetail.status] || []).map((targetSt) => {
                          const isPending = pendingStatus === targetSt;
                          const isClosing = targetSt === "closed";
                          const btnStyle = isPending
                            ? isClosing
                              ? "border-rose-500 bg-rose-600 text-white shadow shadow-rose-950/50"
                              : "border-primary bg-primary text-primary-foreground shadow"
                            : isClosing
                            ? "border-rose-500/40 bg-rose-500/10 text-rose-300 hover:bg-rose-500/20"
                            : "border-white/15 bg-white/[0.05] text-foreground hover:bg-white/[0.1]";
                          return (
                            <button
                              key={targetSt}
                              disabled={transitioning}
                              onClick={() => {
                                if (pendingStatus === targetSt) {
                                  handleApplyStatusTransition(targetSt);
                                } else {
                                  setPendingStatus(targetSt);
                                }
                              }}
                              className={`inline-flex items-center gap-1 rounded-lg border px-3 py-1.5 text-xs font-semibold transition-all ${btnStyle}`}
                            >
                              <ArrowRight className="h-3 w-3" />
                              <span>Passa a {STATUS_CONFIG[targetSt]?.label || targetSt}</span>
                            </button>
                          );
                        })}
                        {(ALLOWED_TRANSITIONS[ticketDetail.status] || []).length === 0 && (
                          <span className="text-xs text-muted-foreground">Nessuna transizione permessa.</span>
                        )}
                      </div>
                    </div>

                    {/* Incident Link Selector */}
                    <div>
                      <div className="text-[11px] font-semibold text-foreground uppercase tracking-wider mb-1.5">
                        Correlazione Incidente Noto
                      </div>
                      <div className="flex items-center gap-2">
                        <select
                          value={incidentLinkSelect}
                          onChange={(e) => setIncidentLinkSelect(e.target.value)}
                          className="rounded-lg border border-white/15 bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:border-primary"
                        >
                          <option value="">Nessun incidente collegato</option>
                          {incidents.map((inc) => (
                            <option key={inc.id} value={inc.id}>
                              {inc.id} — {inc.service}: {inc.title.slice(0, 30)}...
                            </option>
                          ))}
                        </select>
                        <button
                          onClick={handleUpdateIncidentLink}
                          className="rounded-lg border border-primary/40 bg-primary/10 px-2.5 py-1 text-xs font-medium text-primary hover:bg-primary/20"
                        >
                          {incidentLinkSelect ? "Collega" : "Scollega"}
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Optional status note prompt */}
                  {pendingStatus && (
                    <div className="mt-2 pt-2 border-t border-white/10 flex items-center gap-2">
                      <input
                        type="text"
                        value={statusNoteText}
                        onChange={(e) => setStatusNoteText(e.target.value)}
                        placeholder="Nota per il cambio stato (opzionale)..."
                        className="flex-1 rounded-lg border border-white/15 bg-background/80 px-3 py-1 text-xs text-foreground focus:outline-none focus:border-primary"
                      />
                      <button
                        onClick={() => handleApplyStatusTransition(pendingStatus)}
                        disabled={transitioning}
                        className="rounded-lg bg-primary px-3 py-1 text-xs font-semibold text-primary-foreground hover:bg-primary-hover"
                      >
                        {transitioning ? "Applicazione..." : "Conferma Cambio Stato"}
                      </button>
                      <button
                        onClick={() => setPendingStatus(null)}
                        className="text-xs text-muted-foreground hover:text-foreground"
                      >
                        Annulla
                      </button>
                    </div>
                  )}
                </div>

                {/* Structured Diagnostic Findings (4 Blocks) */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {/* Symptoms */}
                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                    <div className="text-[11px] font-bold text-foreground uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <AlertCircle className="h-3.5 w-3.5 text-amber-400" />
                      <span>Sintomi Rilevati</span>
                    </div>
                    <p className="text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed">
                      {ticketDetail.symptoms || "Nessun sintomo registrato."}
                    </p>
                  </div>

                  {/* Steps Attempted */}
                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                    <div className="text-[11px] font-bold text-foreground uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <CheckCircle2 className="h-3.5 w-3.5 text-blue-400" />
                      <span>Verifiche e Passaggi Tentati</span>
                    </div>
                    <p className="text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed">
                      {ticketDetail.attempted_steps || "Nessuna verifica preliminare tentata."}
                    </p>
                  </div>

                  {/* Diagnostic Findings */}
                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                    <div className="text-[11px] font-bold text-foreground uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <Wrench className="h-3.5 w-3.5 text-emerald-400" />
                      <span>Rilievi Diagnostici</span>
                    </div>
                    <p className="text-xs text-muted-foreground whitespace-pre-wrap leading-relaxed">
                      {ticketDetail.diagnostic_findings || "Nessun rilievo diagnostico inserito."}
                    </p>
                  </div>

                  {/* Sources Ref */}
                  <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3">
                    <div className="text-[11px] font-bold text-foreground uppercase tracking-wider mb-1 flex items-center gap-1.5">
                      <BookOpen className="h-3.5 w-3.5 text-primary" />
                      <span>Fonti Knowledge Base</span>
                    </div>
                    {ticketDetail.source_refs && ticketDetail.source_refs.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 mt-1">
                        {ticketDetail.source_refs.map((ref) => (
                          <span
                            key={ref}
                            className="inline-flex items-center gap-1 rounded bg-secondary px-2 py-0.5 font-mono text-[11px] text-secondary-foreground"
                          >
                            <Tag className="h-2.5 w-2.5" />
                            {ref}
                          </span>
                        ))}
                      </div>
                    ) : (
                      <p className="text-xs text-muted-foreground">Nessuna fonte KB consultata.</p>
                    )}
                  </div>
                </div>

                {/* Copilot AI Assistant Chat Panel */}
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-2">
                  <div className="text-xs font-bold text-foreground uppercase tracking-wider flex items-center gap-1.5 mb-1">
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                    <span>Copilota AI per il Tecnico</span>
                  </div>
                  <TechnicianChatPanel
                    ticket={ticketDetail}
                    onApplyProposal={handleApplyAssistantProposal}
                    onGenerateKBProposal={handleGenerateTicketKBProposal}
                    generatingKB={generatingKB}
                  />
                </div>

                {/* Timeline and Notes */}
                <div className="rounded-xl border border-white/10 bg-white/[0.02] p-4 space-y-3">
                  <div className="flex items-center justify-between pb-2 border-b border-white/10">
                    <span className="text-xs font-bold text-foreground uppercase tracking-wider">
                      Cronologia Attività & Note Tecniche
                    </span>
                    <span className="text-[11px] text-muted-foreground">
                      {(ticketDetail.activities ?? []).length} eventi registrati
                    </span>
                  </div>

                  <div className="space-y-2.5">
                    {(ticketDetail.activities ?? []).map((act) => (
                      <div
                        key={act.id}
                        className="rounded-lg border border-white/5 bg-background/50 p-2.5 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between text-[10px] text-muted-foreground">
                          <div className="flex items-center gap-1.5">
                            <span className="font-semibold text-foreground">{act.author}</span>
                            <span className="rounded bg-white/10 px-1 py-0.2 uppercase text-[9px]">
                              {act.author_role}
                            </span>
                            <span className="text-primary font-medium uppercase text-[9px]">
                              • {act.activity_type}
                            </span>
                          </div>
                          <span>{new Date(act.created_at).toLocaleString()}</span>
                        </div>
                        <p className="text-foreground leading-relaxed pl-1">{act.content}</p>
                      </div>
                    ))}
                  </div>

                  {/* Add Note Form */}
                  <form onSubmit={handleAddNote} className="mt-3 pt-3 border-t border-white/10 flex flex-col gap-2">
                    <textarea
                      value={noteContent}
                      onChange={(e) => setNoteContent(e.target.value)}
                      placeholder="Aggiungi una nota tecnica (eventuali password/token verranno redatti automaticamente)..."
                      rows={2}
                      className="w-full rounded-xl border border-white/15 bg-background/80 p-2.5 text-xs text-foreground focus:outline-none focus:border-primary placeholder:text-muted-foreground/60 resize-none"
                    />
                    <div className="flex justify-end">
                      <button
                        type="submit"
                        disabled={submittingNote || !noteContent.trim()}
                        className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary-hover active:scale-95 transition-transform disabled:opacity-50"
                      >
                        {submittingNote ? (
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                        ) : (
                          <Send className="h-3.5 w-3.5" />
                        )}
                        <span>Aggiungi Nota</span>
                      </button>
                    </div>
                  </form>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 2: INCIDENTS VIEW */}
      {activeTab === "incidents" && (
        <div className="flex-1 min-h-0 rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-5 shadow-xl overflow-y-auto custom-scrollbar space-y-4">
          <div className="pb-3 border-b border-white/10">
            <h3 className="text-base font-bold text-foreground">
              Incidenti e Disservizi Noti Aziendali
            </h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Eventi generali condivisi. I ticket individuali possono essere collegati agli incidenti
              per coordinamento, senza fondere né eliminare le richieste originali.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {(incidents ?? []).map((inc) => {
              const statusConf = INCIDENT_STATUS_CONFIG[inc.status] || {
                label: inc.status,
                badge: "bg-muted text-muted-foreground",
              };

              return (
                <div
                  key={inc.id}
                  className="rounded-xl border border-white/10 bg-white/[0.03] p-4 flex flex-col justify-between shadow-md hover:border-white/20 transition-all space-y-3"
                >
                  <div>
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-mono font-bold text-primary text-xs">{inc.id}</span>
                      <span
                        className={`rounded-full border px-2 py-0.5 text-[10px] font-semibold uppercase ${statusConf.badge}`}
                      >
                        {statusConf.label}
                      </span>
                    </div>

                    <div className="mt-2 text-xs font-bold text-foreground">{inc.title}</div>
                    <div className="mt-1 inline-flex items-center gap-1 rounded bg-white/5 px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
                      <span>Servizio:</span>
                      <strong className="text-foreground">{inc.service}</strong>
                    </div>

                    <p className="mt-2 text-xs text-muted-foreground leading-relaxed">
                      {inc.summary}
                    </p>

                    <div className="mt-2.5 rounded-lg bg-black/20 p-2 text-[11px] text-muted-foreground">
                      <span className="font-semibold text-foreground">Sintomi visibili:</span>{" "}
                      {inc.symptoms}
                    </div>
                  </div>

                  <div className="pt-2 border-t border-white/5 flex items-center justify-between text-[11px] text-muted-foreground">
                    <span>
                      Ticket collegati:{" "}
                      <strong className="text-foreground">{inc.ticket_count}</strong>
                    </span>
                    <span>{new Date(inc.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* TAB 3: SUPPORT REQUESTS TABLE (Preserved for compatibility and full audit) */}
      {activeTab === "requests" && (
        <div className="flex-1 min-h-0 rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl shadow-xl overflow-hidden flex flex-col">
          <div className="shrink-0 p-4 border-b border-white/10 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-base font-bold text-foreground">
                Elenco Problematiche IT Registrate
              </h2>
              <p className="text-xs text-muted-foreground">
                Tutte le richieste SupportRequest salvate nel database SQLite.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <label htmlFor="tech-status-filter" className="text-xs font-medium text-muted-foreground">
                Stato:
              </label>
              <select
                id="tech-status-filter"
                value={requestStatusFilter}
                onChange={(e) => setRequestStatusFilter(e.target.value)}
                className="rounded-lg border border-white/15 bg-background px-3 py-1.5 text-xs text-foreground focus:border-primary focus:outline-none"
              >
                <option value="all">Tutti gli stati</option>
                <option value="open">Aperti (open)</option>
                <option value="in_progress">In corso (in_progress)</option>
                <option value="closed">Chiusi (closed)</option>
              </select>
            </div>
          </div>

          {requestsLoading && (requests ?? []).length === 0 ? (
            <div className="flex items-center justify-center p-12 text-xs text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2 text-primary" />
              <span>Caricamento richieste IT...</span>
            </div>
          ) : (requests ?? []).length === 0 ? (
            <div className="flex flex-col items-center justify-center p-12 text-center text-xs text-muted-foreground">
              <FolderOpen className="h-10 w-10 text-muted-foreground/40 mb-3" />
              <h3 className="text-sm font-semibold text-foreground">Nessuna richiesta registrata</h3>
              <p className="mt-1 max-w-sm">
                Non sono presenti problematiche con i filtri attuali.
              </p>
            </div>
          ) : (
            <div className="flex-1 min-h-0 overflow-auto custom-scrollbar">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-border bg-muted/40 text-muted-foreground font-semibold">
                    <th className="py-3 px-4">ID Richiesta</th>
                    <th className="py-3 px-4">Titolo & Descrizione</th>
                    <th className="py-3 px-4">Categoria</th>
                    <th className="py-3 px-4">Stato</th>
                    <th className="py-3 px-4">Thread Collegato</th>
                    <th className="py-3 px-4">Data Creazione (UTC)</th>
                    <th className="py-3 px-4 text-right">Azioni</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/60">
                  {(requests ?? []).map((req) => (
                    <tr key={req.id} className="hover:bg-muted/20 transition-colors">
                      <td className="py-3 px-4 font-mono font-medium text-foreground">{req.id}</td>
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
                      <td className="py-3 px-4 font-mono text-muted-foreground">{req.conversation_id}</td>
                      <td className="py-3 px-4 text-muted-foreground">
                        {new Date(req.created_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        {req.status === "closed" && (
                          <button
                            onClick={() => handleGenerateRequestKBProposal(req.id)}
                            className="inline-flex items-center gap-1 rounded-lg border border-primary/30 bg-primary/10 px-2 py-1 text-[11px] font-semibold text-primary hover:bg-primary/20 active:scale-95 transition-all"
                            title="Genera una bozza di articolo per la Knowledge Base da questa richiesta"
                          >
                            <BookOpen className="h-3 w-3" />
                            <span>Bozza KB</span>
                          </button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* TAB 4: KNOWLEDGE BASE PROPOSALS WORKSPACE */}
      {activeTab === "kb_proposals" && (
        <KnowledgeProposalsPanel
          onSelectTicket={(ticketId) => {
            setSelectedTicketId(ticketId);
            setActiveTab("tickets");
            loadTickets(ticketId);
          }}
        />
      )}
    </section>
  );
};
