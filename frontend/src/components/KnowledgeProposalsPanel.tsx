import React, { useEffect, useState, useCallback } from "react";
import {
  BookOpen,
  RefreshCw,
  AlertCircle,
  Tag,
  Loader2,
  CheckCircle2,
  XCircle,
  Save,
  Eye,
  Edit3,
  ExternalLink,
  Search,
  Sparkles,
} from "lucide-react";
import type {
  KnowledgeProposal,
  DuplicateCandidate,
  ProposalDestination,
} from "../types/api";
import {
  getKnowledgeProposals,
  getKnowledgeProposal,
  updateKnowledgeProposal,
  rejectKnowledgeProposal,
  publishKnowledgeProposal,
  getKnowledgeProposalDuplicates,
} from "../api/client";

const PROPOSAL_STATUS_CONFIG: Record<string, { label: string; badge: string }> = {
  draft: { label: "Bozza", badge: "bg-amber-500/10 text-amber-400 border-amber-500/30" },
  under_review: { label: "In Revisione", badge: "bg-blue-500/10 text-blue-400 border-blue-500/30" },
  approved: { label: "Pubblicato", badge: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30" },
  rejected: { label: "Rifiutato", badge: "bg-rose-500/10 text-rose-400 border-rose-500/30" },
  publishing_failed: { label: "Errore Pubblicazione", badge: "bg-red-500/20 text-red-300 border-red-500/40" },
};

interface KnowledgeProposalsPanelProps {
  onSelectTicket?: (ticketId: string) => void;
}

export const KnowledgeProposalsPanel: React.FC<KnowledgeProposalsPanelProps> = ({
  onSelectTicket,
}) => {
  const [proposals, setProposals] = useState<KnowledgeProposal[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [proposalDetail, setProposalDetail] = useState<KnowledgeProposal | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [detailLoading, setDetailLoading] = useState<boolean>(false);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Edit form state
  const [editTitle, setEditTitle] = useState<string>("");
  const [editMarkdown, setEditMarkdown] = useState<string>("");
  const [editDestination, setEditDestination] = useState<ProposalDestination>("new_document");
  const [editTargetSlug, setEditTargetSlug] = useState<string>("");
  const [editNotes, setEditNotes] = useState<string>("");
  const [activeTab, setActiveTab] = useState<"edit" | "preview">("edit");

  // Actions state
  const [saving, setSaving] = useState<boolean>(false);
  const [publishing, setPublishing] = useState<boolean>(false);
  const [rejecting, setRejecting] = useState<boolean>(false);
  const [rejectionReason, setRejectionReason] = useState<string>("");
  const [showRejectModal, setShowRejectModal] = useState<boolean>(false);

  // Duplicates state
  const [duplicates, setDuplicates] = useState<DuplicateCandidate[]>([]);
  const [checkingDuplicates, setCheckingDuplicates] = useState<boolean>(false);
  const [hasCheckedDuplicates, setHasCheckedDuplicates] = useState<boolean>(false);

  const loadProposals = useCallback(async (selectId?: string) => {
    try {
      setLoading(true);
      setError(null);
      const res = await getKnowledgeProposals(statusFilter);
      const items = res.items || [];
      setProposals(items);

      const targetId =
        selectId ||
        (items.length > 0
          ? selectedId && items.some((p) => p.id === selectedId)
            ? selectedId
            : items[0].id
          : null);
      setSelectedId(targetId);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore caricamento proposte KB");
    } finally {
      setLoading(false);
    }
  }, [statusFilter, selectedId]);

  useEffect(() => {
    loadProposals();
  }, [loadProposals]);

  const loadProposalDetail = useCallback(async (id: string) => {
    try {
      setDetailLoading(true);
      setError(null);
      setSuccessMsg(null);
      setDuplicates([]);
      setHasCheckedDuplicates(false);
      const prop = await getKnowledgeProposal(id);
      setProposalDetail(prop);
      setEditTitle(prop.title || "");
      setEditMarkdown(prop.content_markdown || "");
      setEditDestination(prop.destination || "new_document");
      setEditTargetSlug(prop.target_kb_slug || "");
      setEditNotes(prop.review_notes || "");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore caricamento dettaglio proposta");
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    if (selectedId) {
      loadProposalDetail(selectedId);
    } else {
      setProposalDetail(null);
    }
  }, [selectedId, loadProposalDetail]);

  const handleSave = async () => {
    if (!proposalDetail) return;
    try {
      setSaving(true);
      setError(null);
      setSuccessMsg(null);
      const updated = await updateKnowledgeProposal(proposalDetail.id, {
        title: editTitle.trim(),
        content_markdown: editMarkdown,
        destination: editDestination,
        target_kb_slug: editDestination === "update_existing" ? editTargetSlug.trim() : null,
        notes: editNotes.trim(),
      });
      setProposalDetail(updated);
      setSuccessMsg("Modifiche alla bozza salvate con successo.");
      loadProposals(updated.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore nel salvataggio della proposta");
    } finally {
      setSaving(false);
    }
  };

  const handleCheckDuplicates = async () => {
    if (!proposalDetail) return;
    try {
      setCheckingDuplicates(true);
      setError(null);
      const results = await getKnowledgeProposalDuplicates(proposalDetail.id, 5);
      setDuplicates(results);
      setHasCheckedDuplicates(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore durante la verifica dei duplicati");
    } finally {
      setCheckingDuplicates(false);
    }
  };

  const handlePublish = async () => {
    if (!proposalDetail) return;
    try {
      setPublishing(true);
      setError(null);
      setSuccessMsg(null);
      const updated = await publishKnowledgeProposal(proposalDetail.id, {
        destination: editDestination,
        target_kb_slug: editDestination === "update_existing" ? editTargetSlug.trim() : undefined,
        author: "technician_demo",
      });
      setProposalDetail(updated);
      setSuccessMsg(
        `Articolo approvato e pubblicato con successo in '${updated.published_path || "knowledge_base"}'. Indice RAG aggiornato!`
      );
      loadProposals(updated.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore durante la pubblicazione");
    } finally {
      setPublishing(false);
    }
  };

  const handleReject = async () => {
    if (!proposalDetail) return;
    try {
      setRejecting(true);
      setError(null);
      setSuccessMsg(null);
      const updated = await rejectKnowledgeProposal(
        proposalDetail.id,
        rejectionReason.trim() || undefined,
        "technician_demo"
      );
      setProposalDetail(updated);
      setShowRejectModal(false);
      setRejectionReason("");
      setSuccessMsg("Proposta KB rifiutata.");
      loadProposals(updated.id);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore durante il rifiuto della proposta");
    } finally {
      setRejecting(false);
    }
  };

  return (
    <div className="flex-1 min-h-0 rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl shadow-xl overflow-hidden flex flex-col md:flex-row">
      {/* LEFT COLUMN: Proposals List */}
      <div className="w-full md:w-80 lg:w-96 border-b md:border-b-0 md:border-r border-white/10 flex flex-col shrink-0 bg-background/30">
        <div className="p-3 border-b border-white/10 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4 text-primary" />
            <h3 className="text-xs font-bold text-foreground">Proposte Articoli KB</h3>
            <span className="rounded-full bg-primary/20 px-1.5 py-0.2 text-[10px] font-semibold text-primary">
              {proposals.length}
            </span>
          </div>

          <button
            onClick={() => loadProposals()}
            disabled={loading}
            aria-label="Ricarica proposte"
            className="rounded-lg border border-white/10 p-1 text-muted-foreground hover:text-foreground hover:bg-white/5"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
          </button>
        </div>

        {/* Filter Pills */}
        <div className="p-2 border-b border-white/5 flex flex-wrap gap-1 bg-white/[0.01]">
          {["all", "draft", "approved", "rejected"].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`rounded-lg px-2 py-1 text-[11px] font-medium transition-all ${
                statusFilter === st
                  ? "bg-primary text-primary-foreground shadow"
                  : "text-muted-foreground hover:bg-white/5 hover:text-foreground"
              }`}
            >
              {st === "all" ? "Tutte" : PROPOSAL_STATUS_CONFIG[st]?.label || st}
            </button>
          ))}
        </div>

        {/* List items */}
        <div className="flex-1 min-h-0 overflow-y-auto divide-y divide-white/5 custom-scrollbar">
          {loading && proposals.length === 0 ? (
            <div className="flex items-center justify-center p-8 text-xs text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin mr-2 text-primary" />
              <span>Caricamento proposte...</span>
            </div>
          ) : proposals.length === 0 ? (
            <div className="flex flex-col items-center justify-center p-8 text-center text-xs text-muted-foreground">
              <BookOpen className="h-8 w-8 text-muted-foreground/30 mb-2" />
              <p className="font-semibold text-foreground">Nessuna proposta trovata</p>
              <p className="text-[11px] max-w-xs mt-1">
                Le bozze vengono generate automaticamente dai ticket risolti o dalle conferme degli utenti in chat.
              </p>
            </div>
          ) : (
            proposals.map((prop) => {
              const isSelected = prop.id === selectedId;
              const statusConf = PROPOSAL_STATUS_CONFIG[prop.status] || {
                label: prop.status,
                badge: "bg-muted text-muted-foreground",
              };

              return (
                <button
                  key={prop.id}
                  onClick={() => setSelectedId(prop.id)}
                  className={`w-full text-left p-3 transition-colors flex flex-col gap-1.5 ${
                    isSelected ? "bg-white/10 border-l-2 border-primary" : "hover:bg-white/[0.04]"
                  }`}
                >
                  <div className="flex items-center justify-between gap-1 text-[10px]">
                    <span className="font-mono text-muted-foreground">{prop.id}</span>
                    <span className={`rounded-full border px-2 py-0.2 font-semibold uppercase ${statusConf.badge}`}>
                      {statusConf.label}
                    </span>
                  </div>

                  <div className="text-xs font-semibold text-foreground line-clamp-1">{prop.title}</div>

                  <div className="flex items-center justify-between gap-2 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <Tag className="h-2.5 w-2.5 text-primary" />
                      <span>{prop.generated_category || prop.source_type}</span>
                    </span>
                    <span>{new Date(prop.created_at).toLocaleDateString()}</span>
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* RIGHT COLUMN: Proposal Detail & Review Workspace */}
      <div className="flex-1 min-h-0 flex flex-col overflow-y-auto p-4 custom-scrollbar space-y-4">
        {detailLoading ? (
          <div className="flex items-center justify-center h-full py-16 text-xs text-muted-foreground">
            <Loader2 className="h-6 w-6 animate-spin text-primary mb-2" />
            <span className="ml-2">Caricamento dettaglio bozza KB...</span>
          </div>
        ) : !proposalDetail ? (
          <div className="flex flex-col items-center justify-center h-full py-16 text-center text-xs text-muted-foreground">
            <BookOpen className="h-10 w-10 text-muted-foreground/30 mb-2" />
            <p className="font-semibold text-foreground">Nessuna proposta selezionata</p>
            <p className="text-[11px] max-w-sm mt-1">
              Seleziona una bozza di articolo a sinistra per revisionarla, verificare duplicati semantici e approvarla per la pubblicazione.
            </p>
          </div>
        ) : (
          <>
            {/* Alerts */}
            {error && (
              <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span className="flex-1">{error}</span>
                <button onClick={() => setError(null)} className="hover:underline text-[11px]">
                  Chiudi
                </button>
              </div>
            )}

            {successMsg && (
              <div className="rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4 shrink-0" />
                <span className="flex-1">{successMsg}</span>
                <button onClick={() => setSuccessMsg(null)} className="hover:underline text-[11px]">
                  Chiudi
                </button>
              </div>
            )}

            {/* Header & Meta */}
            <div className="flex flex-col gap-3 pb-3 border-b border-white/10">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <code className="text-sm font-mono font-bold text-primary bg-primary/10 border border-primary/20 px-2 py-0.5 rounded-lg">
                    {proposalDetail.id}
                  </code>
                  <span
                    className={`rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase ${
                      PROPOSAL_STATUS_CONFIG[proposalDetail.status]?.badge || "bg-muted"
                    }`}
                  >
                    {PROPOSAL_STATUS_CONFIG[proposalDetail.status]?.label || proposalDetail.status}
                  </span>
                  <span className="rounded-md bg-white/5 border border-white/10 px-2 py-0.5 text-[10px] text-muted-foreground">
                    Fonte: <strong className="text-foreground">{proposalDetail.source_type}</strong> (<code>{proposalDetail.source_id}</code>)
                  </span>
                  {proposalDetail.source_type === "ticket" && onSelectTicket && (
                    <button
                      onClick={() => onSelectTicket(proposalDetail.source_id)}
                      className="inline-flex items-center gap-1 text-[11px] text-primary hover:underline"
                    >
                      <span>Vedi Ticket</span>
                      <ExternalLink className="h-3 w-3" />
                    </button>
                  )}
                </div>

                <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                  <span>Autore: <strong className="text-foreground">{proposalDetail.author}</strong></span>
                  <span>• Creato: {new Date(proposalDetail.created_at).toLocaleString()}</span>
                </div>
              </div>

              {/* Title input */}
              <div className="space-y-1">
                <label className="text-[11px] font-bold text-foreground uppercase tracking-wider">
                  Titolo Articolo Knowledge Base
                </label>
                <input
                  type="text"
                  value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)}
                  disabled={proposalDetail.status !== "draft" && proposalDetail.status !== "under_review"}
                  className="w-full rounded-xl border border-white/15 bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-primary font-semibold disabled:opacity-60"
                />
              </div>

              {/* Destination selector */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                <div className="space-y-1">
                  <label className="text-[11px] font-bold text-foreground uppercase tracking-wider">
                    Destinazione Pubblicazione
                  </label>
                  <div className="flex items-center gap-2">
                    <label className="flex items-center gap-1.5 text-xs text-foreground cursor-pointer">
                      <input
                        type="radio"
                        name="dest"
                        value="new_document"
                        checked={editDestination === "new_document"}
                        onChange={() => setEditDestination("new_document")}
                        disabled={proposalDetail.status !== "draft" && proposalDetail.status !== "under_review"}
                      />
                      <span>Nuovo Articolo</span>
                    </label>
                    <label className="flex items-center gap-1.5 text-xs text-foreground cursor-pointer">
                      <input
                        type="radio"
                        name="dest"
                        value="update_existing"
                        checked={editDestination === "update_existing"}
                        onChange={() => setEditDestination("update_existing")}
                        disabled={proposalDetail.status !== "draft" && proposalDetail.status !== "under_review"}
                      />
                      <span>Aggiorna Esistente</span>
                    </label>
                  </div>
                </div>

                {editDestination === "update_existing" && (
                  <div className="space-y-1">
                    <label className="text-[11px] font-bold text-foreground uppercase tracking-wider">
                      Nome file / Slug esistente (.md)
                    </label>
                    <input
                      type="text"
                      value={editTargetSlug}
                      onChange={(e) => setEditTargetSlug(e.target.value)}
                      placeholder="es. wifi.md oppure procedura-reset-password.md"
                      disabled={proposalDetail.status !== "draft" && proposalDetail.status !== "under_review"}
                      className="w-full rounded-lg border border-white/15 bg-background px-3 py-1 text-xs text-foreground focus:outline-none focus:border-primary"
                    />
                  </div>
                )}
              </div>
            </div>

            {/* Semantic Duplicate Detection Section */}
            <div className="rounded-xl border border-white/10 bg-white/[0.02] p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-xs font-bold text-foreground">
                  <Search className="h-3.5 w-3.5 text-primary" />
                  <span>Verifica Duplicati e Sovrapposizioni (Chroma RAG)</span>
                </div>
                <button
                  type="button"
                  onClick={handleCheckDuplicates}
                  disabled={checkingDuplicates}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-white/15 bg-white/5 px-2.5 py-1 text-xs font-medium text-foreground hover:bg-white/10 active:scale-95 transition-all disabled:opacity-50"
                >
                  {checkingDuplicates ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Sparkles className="h-3 w-3 text-primary" />
                  )}
                  <span>Cerca Articoli Simili</span>
                </button>
              </div>

              {hasCheckedDuplicates && duplicates.length === 0 && (
                <div className="text-[11px] text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 rounded-lg p-2 flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 shrink-0" />
                  <span>Nessun articolo duplicato o fortemente sovrapposto rilevato nella Knowledge Base.</span>
                </div>
              )}

              {duplicates.length > 0 && (
                <div className="space-y-1.5 pt-1">
                  <span className="text-[10px] text-muted-foreground">
                    Articoli esistenti con similitudine semantica:
                  </span>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                    {duplicates.map((dup) => (
                      <div
                        key={dup.slug}
                        className="rounded-lg border border-white/10 bg-black/20 p-2 text-xs space-y-1"
                      >
                        <div className="flex items-center justify-between gap-1">
                          <span className="font-semibold text-foreground truncate">{dup.title}</span>
                          <span className="font-mono text-[10px] text-amber-400 font-bold">
                            {(dup.similarity * 100).toFixed(0)}% sim.
                          </span>
                        </div>
                        <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                          <span className="font-mono">{dup.doc_id}</span>
                          <span>• {dup.slug}</span>
                        </div>
                        <p className="text-[11px] text-muted-foreground line-clamp-2 italic">
                          {dup.preview}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Markdown Editor & Preview Tabs */}
            <div className="rounded-xl border border-white/10 bg-white/[0.02] flex flex-col overflow-hidden">
              <div className="border-b border-white/10 px-3 py-1.5 bg-background/50 flex items-center justify-between">
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setActiveTab("edit")}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg transition-colors ${
                      activeTab === "edit"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Edit3 className="h-3 w-3" />
                    <span>Modifica Markdown</span>
                  </button>
                  <button
                    onClick={() => setActiveTab("preview")}
                    className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded-lg transition-colors ${
                      activeTab === "preview"
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <Eye className="h-3 w-3" />
                    <span>Anteprima</span>
                  </button>
                </div>

                <span className="text-[10px] text-muted-foreground">
                  Include Front Matter YAML e sezioni strutturate
                </span>
              </div>

              {activeTab === "edit" ? (
                <textarea
                  value={editMarkdown}
                  onChange={(e) => setEditMarkdown(e.target.value)}
                  disabled={proposalDetail.status !== "draft" && proposalDetail.status !== "under_review"}
                  rows={14}
                  className="w-full p-3 bg-black/40 font-mono text-xs text-foreground focus:outline-none resize-y custom-scrollbar leading-relaxed disabled:opacity-60"
                  placeholder="Contenuto Markdown con front matter YAML..."
                />
              ) : (
                <div className="p-4 bg-black/30 text-xs text-foreground max-h-96 overflow-y-auto custom-scrollbar whitespace-pre-wrap leading-relaxed font-sans">
                  {editMarkdown || "Nessun contenuto Markdown."}
                </div>
              )}
            </div>

            {/* Notes & Actions Bar */}
            <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 pt-2 border-t border-white/10">
              <div className="flex-1">
                <input
                  type="text"
                  value={editNotes}
                  onChange={(e) => setEditNotes(e.target.value)}
                  placeholder="Note del revisore tecnico (opzionali)..."
                  disabled={proposalDetail.status !== "draft" && proposalDetail.status !== "under_review"}
                  className="w-full rounded-xl border border-white/15 bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-primary disabled:opacity-60"
                />
              </div>

              <div className="flex flex-wrap items-center gap-2">
                {/* Save Draft Button */}
                {(proposalDetail.status === "draft" || proposalDetail.status === "under_review") && (
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-white/15 bg-white/5 px-3 py-1.5 text-xs font-semibold text-foreground hover:bg-white/10 active:scale-95 transition-all disabled:opacity-50"
                  >
                    {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Save className="h-3.5 w-3.5" />}
                    <span>Salva Bozza</span>
                  </button>
                )}

                {/* Reject Button */}
                {(proposalDetail.status === "draft" || proposalDetail.status === "under_review") && (
                  <button
                    onClick={() => setShowRejectModal(true)}
                    disabled={rejecting}
                    className="inline-flex items-center gap-1.5 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-1.5 text-xs font-semibold text-rose-300 hover:bg-rose-500/20 active:scale-95 transition-all disabled:opacity-50"
                  >
                    <XCircle className="h-3.5 w-3.5" />
                    <span>Rifiuta</span>
                  </button>
                )}

                {/* Approve & Publish Button */}
                {(proposalDetail.status === "draft" || proposalDetail.status === "under_review") && (
                  <button
                    onClick={handlePublish}
                    disabled={publishing}
                    className="inline-flex items-center gap-1.5 rounded-xl bg-primary px-3 py-1.5 text-xs font-bold text-primary-foreground hover:bg-primary-hover active:scale-95 transition-all shadow-md disabled:opacity-50"
                  >
                    {publishing ? (
                      <Loader2 className="h-3.5 w-3.5 animate-spin" />
                    ) : (
                      <CheckCircle2 className="h-3.5 w-3.5" />
                    )}
                    <span>Approva e Pubblica Articolo</span>
                  </button>
                )}
              </div>
            </div>

            {/* Rejection Modal / Prompt */}
            {showRejectModal && (
              <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
                <div className="w-full max-w-md rounded-2xl border border-white/10 bg-card p-5 shadow-2xl space-y-3">
                  <div className="flex items-center gap-2 text-rose-400 font-bold text-sm">
                    <XCircle className="h-4 w-4" />
                    <span>Conferma Rifiuto Proposta KB</span>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    La proposta verrà contrassegnata come rifiutata e non sarà pubblicata nella Knowledge Base.
                  </p>
                  <textarea
                    value={rejectionReason}
                    onChange={(e) => setRejectionReason(e.target.value)}
                    placeholder="Motivo del rifiuto (es. Procedura obsoleta, duplicato di KB-AUTH-001)..."
                    rows={3}
                    className="w-full rounded-xl border border-white/15 bg-background p-2.5 text-xs text-foreground focus:outline-none focus:border-primary resize-none"
                  />
                  <div className="flex justify-end gap-2 pt-2">
                    <button
                      onClick={() => setShowRejectModal(false)}
                      className="rounded-xl px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground"
                    >
                      Annulla
                    </button>
                    <button
                      onClick={handleReject}
                      disabled={rejecting}
                      className="rounded-xl bg-rose-600 px-3 py-1.5 text-xs font-bold text-white hover:bg-rose-500"
                    >
                      {rejecting ? "Rifiuto..." : "Conferma Rifiuto"}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};
