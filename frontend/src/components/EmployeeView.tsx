import React, { useEffect, useState, useCallback, useRef } from "react";
import {
  MessageSquare,
  Plus,
  Send,
  FilePlus,
  Clock,
  User,
  AlertCircle,
  Loader2,
  Tag,
  Bot,
  BookOpen,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Sparkles,
  ShieldAlert,
  Wrench,
  CheckCircle2,
  Check,
} from "lucide-react";
import type { ConversationDetail, ConversationSummary, KBSourceItem, SupportRequestItem } from "../types/api";
import {
  confirmConversationResolution,
  confirmSupportRequestResolution,
  createConversation,
  createSupportRequest,
  getConversation,
  getConversations,
  reopenSupportRequest,
  sendMessage,
  triggerAssistantTurn,
} from "../api/client";
import { useHealth } from "../hooks/useHealth";
import { MarkdownMessage } from "./MarkdownMessage";
import { NewRequestModal } from "./NewRequestModal";

type AssistantStatus = "ready" | "sending" | "thinking" | "retrieving" | "failed";

const RESOLUTION_REGEX =
  /(?:la problematica è da considerarsi completamente risolta|ti chiedo conferma:?\s*la problematica|confermi che.*risolt[oa]|problema.*risolto|richiesta.*risolta)/i;

export const EmployeeView: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [assistantStatus, setAssistantStatus] = useState<AssistantStatus>("ready");
  const [assistantError, setAssistantError] = useState<string | null>(null);
  const [generalError, setGeneralError] = useState<string | null>(null);
  const [inputText, setInputText] = useState<string>("");
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [expandedSources, setExpandedSources] = useState<Record<string, boolean>>({});

  // Bot-resolved confirmation & 2-minute auto-close timer
  const [secondsLeft, setSecondsLeft] = useState<number | null>(null);
  const [confirmingResolution, setConfirmingResolution] = useState<boolean>(false);
  const [dismissedRequests, setDismissedRequests] = useState<Record<string, boolean>>({});
  const [resolutionNotice, setResolutionNotice] = useState<string | null>(null);


  const { data: healthData } = useHealth();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  const loadConversations = useCallback(async (selectNewestId?: string) => {
    try {
      setLoading(true);
      setGeneralError(null);
      const listData = await getConversations(50, 0);
      setConversations(listData.items);

      const targetId = selectNewestId || (listData.items.length > 0 ? listData.items[0].id : null);
      setSelectedId(targetId);

      if (targetId) {
        const detailData = await getConversation(targetId);
        setDetail(detailData);
      } else {
        setDetail(null);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setGeneralError(err.message);
      } else {
        setGeneralError("Impossibile caricare le conversazioni");
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    scrollToBottom();
  }, [detail?.messages, assistantStatus]);

  const handleSelectConversation = async (id: string) => {
    try {
      setSelectedId(id);
      setGeneralError(null);
      setAssistantError(null);
      setSecondsLeft(null);
      setResolutionNotice(null);
      setAssistantStatus("ready");
      const detailData = await getConversation(id);
      setDetail(detailData);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setGeneralError(err.message);
      }
    }
  };

  const handleCreateNewThread = async () => {
    try {
      setLoading(true);
      setGeneralError(null);
      setAssistantError(null);
      setSecondsLeft(null);
      setResolutionNotice(null);
      setAssistantStatus("ready");
      const newConv = await createConversation("Nuova Richiesta IT");
      await loadConversations(newConv.id);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setGeneralError(err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  // Derived state for Bot-Resolution confirmation prompt
  const activeRequest = detail?.requests?.find((r) => r.status === "open");
  const activeTicket = detail?.messages
    ?.slice()
    ?.reverse()
    ?.find((m) => m.metadata_json?.ticket_id)?.metadata_json;

  const lastAssistantMsg = detail?.messages
    ?.slice()
    ?.reverse()
    ?.find((m) => m.role === "assistant");

  const hasResolutionPhrase = Boolean(
    lastAssistantMsg?.content && RESOLUTION_REGEX.test(lastAssistantMsg.content)
  );

  const requestKey = activeRequest?.id || (selectedId ? `conv_${selectedId}` : "");

  // Only eligible if bot-resolved without an active technician ticket
  const isResolutionSuggested =
    !activeTicket?.ticket_id &&
    Boolean(requestKey) &&
    !dismissedRequests[requestKey] &&
    (hasResolutionPhrase ||
      Boolean(lastAssistantMsg?.metadata_json?.resolution_proposed) ||
      lastAssistantMsg?.metadata_json?.phase === "finalization" ||
      activeRequest?.phase === "finalization" ||
      activeRequest?.outcome === "resolved_unconfirmed");

  const isConversationResolved = Boolean(
    detail &&
      (detail.status === "archived" ||
        (detail.requests &&
          detail.requests.length > 0 &&
          detail.requests.every((r) => r.status === "closed")))
  );

  const handleConfirmResolution = useCallback(
    async (requestId: string | null, confirmedByUser: boolean) => {
      try {
        setConfirmingResolution(true);
        let updated: SupportRequestItem | null = null;
        if (requestId) {
          updated = await confirmSupportRequestResolution(requestId, confirmedByUser);
        } else if (selectedId) {
          updated = await confirmConversationResolution(selectedId, confirmedByUser);
        } else {
          return;
        }

        setSecondsLeft(null);
        setResolutionNotice(
          confirmedByUser
            ? "Richiesta IT contrassegnata come risolta e chiusa con successo."
            : "Richiesta IT chiusa automaticamente come risolta (scadenza timer 2 minuti)."
        );

        if (updated) {
          setDetail((prev) => {
            if (!prev) return null;
            const exists = prev.requests.some((r) => r.id === updated.id);
            return {
              ...prev,
              status: "archived",
              requests: exists
                ? prev.requests.map((r) => (r.id === updated.id ? updated : r))
                : [...prev.requests, updated],
            };
          });
        }

        const listData = await getConversations(50, 0);
        setConversations(listData.items);
      } catch (err: unknown) {
        setGeneralError(err instanceof Error ? err.message : "Errore conferma risoluzione");
      } finally {
        setConfirmingResolution(false);
      }
    },
    [selectedId]
  );

  const handleContinueConversation = async (requestId: string | null) => {
    try {
      setSecondsLeft(null);
      const dismissKey = requestId || (selectedId ? `conv_${selectedId}` : "");
      if (dismissKey) {
        setDismissedRequests((prev) => ({ ...prev, [dismissKey]: true }));
      }
      if (requestId) {
        const updated = await reopenSupportRequest(requestId);
        setDetail((prev) => {
          if (!prev) return null;
          return {
            ...prev,
            status: "active",
            requests: prev.requests.map((r) => (r.id === requestId ? updated : r)),
          };
        });
      }
    } catch (err: unknown) {
      setGeneralError(err instanceof Error ? err.message : "Errore continuazione conversazione");
    }
  };

  // Timer initialization when resolution is suggested
  useEffect(() => {
    if (isResolutionSuggested) {
      setSecondsLeft((prev) => (prev === null ? 120 : prev));
    } else {
      setSecondsLeft((prev) => (prev !== null ? null : prev));
    }
  }, [isResolutionSuggested]);

  // Countdown decrement & auto-confirm at 00:00
  useEffect(() => {
    if (!isResolutionSuggested || secondsLeft === null) return;

    if (secondsLeft <= 0) {
      handleConfirmResolution(activeRequest?.id || null, false);
      return;
    }

    const timer = setInterval(() => {
      setSecondsLeft((prev) => (prev !== null && prev > 0 ? prev - 1 : 0));
    }, 1000);

    return () => clearInterval(timer);
  }, [isResolutionSuggested, secondsLeft, activeRequest, handleConfirmResolution]);


  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || !selectedId || assistantStatus !== "ready" || isConversationResolved) return;

    const content = inputText.trim();
    setInputText("");
    setAssistantError(null);

    // If user types while a resolution prompt is pending, dismiss it since they are continuing
    const currentDismissKey = activeRequest?.id || (selectedId ? `conv_${selectedId}` : "");
    if (currentDismissKey) {
      setDismissedRequests((prev) => ({ ...prev, [currentDismissKey]: true }));
      setSecondsLeft(null);
    }

    try {
      // Step 1: Send user message
      setAssistantStatus("sending");
      const savedMsg = await sendMessage(selectedId, content);

      // Append user message locally
      setDetail((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          updated_at: savedMsg.created_at,
          messages: [...prev.messages, savedMsg],
        };
      });

      // Step 2: Trigger Assistant turn
      setAssistantStatus("thinking");
      const turnResult = await triggerAssistantTurn(selectedId);

      // Append assistant message & sync requests
      setDetail((prev) => {
        if (!prev) return null;
        let updatedRequests = prev.requests;
        if (turnResult.request_id) {
          const exists = prev.requests.some((r) => r.id === turnResult.request_id);
          if (!exists) {
            updatedRequests = [
              ...prev.requests,
              {
                id: turnResult.request_id,
                conversation_id: selectedId,
                title: "Richiesta IT",
                description: "",
                initial_category: "general",
                final_category: null,
                status: "open",
                phase: turnResult.phase,
                outcome: turnResult.resolution_proposed ? "resolved_unconfirmed" : null,
                created_at: new Date().toISOString(),
                updated_at: new Date().toISOString(),
              },
            ];
          } else if (turnResult.resolution_proposed) {
            updatedRequests = prev.requests.map((r) =>
              r.id === turnResult.request_id
                ? { ...r, phase: turnResult.phase, outcome: "resolved_unconfirmed" }
                : r
            );
          }
        } else if (turnResult.resolution_proposed) {
          updatedRequests = prev.requests.map((r) =>
            r.status === "open"
              ? { ...r, phase: turnResult.phase, outcome: "resolved_unconfirmed" }
              : r
          );
        }

        return {
          ...prev,
          updated_at: turnResult.message.created_at,
          messages: [...prev.messages, turnResult.message],
          requests: updatedRequests,
        };
      });

      // If the assistant just returned a resolution prompt, clear dismissal so the prompt appears
      if (
        turnResult.resolution_proposed ||
        RESOLUTION_REGEX.test(turnResult.message.content)
      ) {
        const newKey = turnResult.request_id || (selectedId ? `conv_${selectedId}` : "");
        if (newKey) {
          setDismissedRequests((prev) => {
            const next = { ...prev };
            delete next[newKey];
            return next;
          });
        }
      }

      setAssistantStatus("ready");

      // Refresh list to update message counter and order
      const listData = await getConversations(50, 0);
      setConversations(listData.items);
    } catch (err: unknown) {
      setAssistantStatus("failed");
      if (err instanceof Error) {
        setAssistantError(err.message);
      } else {
        setAssistantError("Errore durante l'elaborazione dell'assistente");
      }
    }
  };


  const handleRetryAssistantTurn = async () => {
    if (!selectedId || assistantStatus !== "failed") return;
    setAssistantError(null);
    try {
      setAssistantStatus("thinking");
      const turnResult = await triggerAssistantTurn(selectedId);

      setDetail((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          updated_at: turnResult.message.created_at,
          messages: [...prev.messages, turnResult.message],
        };
      });

      setAssistantStatus("ready");

      const listData = await getConversations(50, 0);
      setConversations(listData.items);
    } catch (err: unknown) {
      setAssistantStatus("failed");
      if (err instanceof Error) {
        setAssistantError(err.message);
      } else {
        setAssistantError("Errore durante il tentativo di riprova");
      }
    }
  };

  const handleCreateSupportRequest = async (
    title: string,
    description: string,
    category: string
  ) => {
    if (!selectedId) return;
    const newReq = await createSupportRequest(selectedId, title, description, category);

    setDetail((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        requests: [newReq, ...prev.requests],
      };
    });

    const listData = await getConversations(50, 0);
    setConversations(listData.items);
  };

  const toggleSources = (msgId: string) => {
    setExpandedSources((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const isGeminiAvailable = healthData?.gemini_configured !== false;

  return (
    <section
      id="panel-employee"
      role="tabpanel"
      aria-labelledby="tab-employee"
      className="grid grid-cols-1 gap-4 lg:gap-6 lg:grid-cols-12 h-full min-h-0"
    >
      {/* Sidebar: Conversation Threads */}
      <div className="flex flex-col rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-4 shadow-xl lg:col-span-4 h-full min-h-0 overflow-hidden">
        <div className="flex items-center justify-between pb-4 border-b border-white/10 shrink-0">
          <div className="flex items-center gap-2">
            <MessageSquare className="h-5 w-5 text-primary" />
            <h2 className="text-base font-bold text-foreground">Conversazioni</h2>
          </div>
          <button
            onClick={handleCreateNewThread}
            disabled={loading}
            aria-label="Crea Nuova Conversazione"
            className="inline-flex items-center gap-1.5 rounded-lg bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary-hover active:scale-95 transition-transform"
          >
            <Plus className="h-3.5 w-3.5" />
            <span>Nuova Chat</span>
          </button>
        </div>

        {/* Conversation List */}
        <div className="mt-3 flex-1 min-h-0 overflow-y-auto space-y-2 pr-1 custom-scrollbar">
          {loading && conversations.length === 0 ? (
            <div className="flex items-center justify-center p-8 text-xs text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2 text-primary" />
              <span>Caricamento conversazioni...</span>
            </div>
          ) : conversations.length === 0 ? (
            <div className="rounded-xl border border-dashed border-white/10 p-6 text-center text-xs text-muted-foreground">
              <p>Nessuna conversazione presente.</p>
              <button
                onClick={handleCreateNewThread}
                className="mt-3 text-xs font-semibold text-primary underline"
              >
                Inizia la prima sessione
              </button>
            </div>
          ) : (
            conversations.map((conv) => {
              const isSelected = conv.id === selectedId;
              return (
                <button
                  key={conv.id}
                  onClick={() => handleSelectConversation(conv.id)}
                  className={`w-full text-left rounded-xl p-3 text-xs transition-all border ${
                    isSelected
                      ? "border-primary/80 bg-primary/20 shadow-md backdrop-blur-md"
                      : "border-white/5 bg-white/[0.03] hover:bg-white/[0.08] hover:border-white/10"
                  }`}
                >
                  <div className="flex items-center justify-between font-semibold text-foreground">
                    <span className="truncate max-w-[190px]" title={`${conv.title || "Richiesta IT"}${conv.category ? ` (${conv.category})` : ""}`}>
                      {conv.title || "Richiesta IT"}
                      {conv.category ? (
                        <span className="font-normal text-muted-foreground ml-1">({conv.category})</span>
                      ) : null}
                    </span>
                    <span className="text-[10px] text-muted-foreground flex items-center gap-1 shrink-0 ml-1">
                      <Clock className="h-3 w-3" />
                      {new Date(conv.updated_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center justify-between text-[11px] text-muted-foreground">
                    <div className="flex items-center gap-2">
                      <span>{conv.message_count} messaggi</span>
                      {conv.request_count > 0 && (
                        <span className="rounded bg-accent px-1.5 py-0.5 text-[10px] text-accent-foreground font-medium">
                          {conv.request_count} problemi IT
                        </span>
                      )}
                    </div>
                    {conv.status === "archived" ? (
                      <span className="rounded border border-rose-500/40 bg-rose-500/20 px-1.5 py-0.5 text-[9px] font-bold text-rose-300 uppercase shadow-sm shadow-rose-950/30">
                        Chiuso
                      </span>
                    ) : (
                      <span className="rounded border border-emerald-500/40 bg-emerald-500/20 px-1.5 py-0.5 text-[9px] font-bold text-emerald-300 uppercase shadow-sm">
                        Attivo
                      </span>
                    )}
                  </div>
                </button>
              );
            })
          )}
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex flex-col rounded-2xl border border-white/10 bg-card/60 backdrop-blur-xl p-4 shadow-xl lg:col-span-8 h-full min-h-0 overflow-hidden">
        {/* Thread Header */}
        <div className="flex flex-col gap-2 pb-4 border-b border-border/80 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-foreground">
                {detail?.title || "Seleziona o crea una conversazione"}
                {detail?.category ? (
                  <span className="text-sm font-normal text-muted-foreground ml-1.5">
                    ({detail.category})
                  </span>
                ) : null}
              </h2>
              {detail && (
                detail.status === "archived" ? (
                  <span className="rounded-full border border-rose-500/50 bg-rose-500/20 px-2.5 py-0.5 text-[10px] font-bold text-rose-300 uppercase shadow-sm shadow-rose-950/40">
                    Chiuso
                  </span>
                ) : (
                  <span className="rounded-full border border-emerald-500/50 bg-emerald-500/20 px-2.5 py-0.5 text-[10px] font-bold text-emerald-300 uppercase shadow-sm">
                    Attivo
                  </span>
                )
              )}
            </div>
            {detail && (
              <p className="text-xs text-muted-foreground mt-0.5">
                Thread ID: <code className="font-mono text-[11px] text-foreground">{detail.id}</code> • Utente demo:{" "}
                <span className="text-foreground">{detail.user_id}</span>
              </p>
            )}
          </div>

          {detail && (
            <button
              onClick={() => setIsModalOpen(true)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-primary/50 bg-primary/10 px-3 py-1.5 text-xs font-semibold text-primary hover:bg-primary/20 active:scale-95 transition-transform"
            >
              <FilePlus className="h-4 w-4" />
              <span>Segnala Problema IT</span>
            </button>
          )}
        </div>

        {/* Missing Gemini Key Warning Banner */}
        {!isGeminiAvailable && (
          <div className="mt-3 flex items-start gap-2 rounded-xl border border-amber-500/30 bg-amber-500/10 p-3 text-xs text-amber-200">
            <ShieldAlert className="h-4 w-4 shrink-0 text-amber-400 mt-0.5" />
            <p className="leading-relaxed">
              <strong>Assistente AI non configurato:</strong> La chiave <code className="font-mono font-semibold">GEMINI_API_KEY</code> non è impostata nel file <code className="font-mono">.env</code> del backend. Le risposte automatiche dell&apos;assistente sono disabilitate fino alla configurazione della chiave.
            </p>
          </div>
        )}

        {/* General Error notification */}
        {generalError && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{generalError}</span>
          </div>
        )}

        {/* Registered Requests Pill Header */}
        {detail && detail.requests && detail.requests.length > 0 && (
          <div className="mt-3 space-y-1.5">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Richieste IT associate a questo thread:
            </span>
            <div className="flex flex-wrap gap-2">
              {detail.requests.map((req) => {
                const isClosed = req.status === "closed";
                const isResolved = req.status === "resolved";
                const statusClass = isClosed
                  ? "border-rose-500/40 bg-rose-500/20 text-rose-300"
                  : isResolved
                  ? "border-emerald-500/40 bg-emerald-500/20 text-emerald-300"
                  : "border-amber-500/40 bg-amber-500/20 text-amber-300";
                const statusLabel = isClosed ? "Chiuso" : isResolved ? "Risolto" : "Aperto";

                return (
                  <div
                    key={req.id}
                    className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1 text-xs"
                  >
                    <Tag className="h-3 w-3 text-primary" />
                    <span className="font-medium text-foreground">{req.title}</span>
                    <span className={`rounded border px-1.5 py-0.2 text-[10px] uppercase font-semibold ${statusClass}`}>
                      {statusLabel}
                    </span>
                    {req.phase && (
                      <span className="rounded bg-primary/20 px-1 text-[10px] text-primary uppercase font-medium">
                        {req.phase}
                      </span>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Active Ticket Escalation Banner */}
        {(() => {
          const activeTicket = detail?.messages
            ?.slice()
            ?.reverse()
            ?.find((m) => m.metadata_json?.ticket_id)?.metadata_json;

          if (!activeTicket?.ticket_id) return null;

          const st = (activeTicket.ticket_status || "open").toLowerCase();
          const stColor =
            st === "closed"
              ? "bg-rose-500/20 text-rose-300 border-rose-500/50 shadow-sm shadow-rose-950/40"
              : st === "resolved"
              ? "bg-emerald-500/20 text-emerald-300 border-emerald-500/40 shadow-sm"
              : st === "in_progress"
              ? "bg-blue-500/20 text-blue-300 border-blue-500/40 shadow-sm"
              : "bg-amber-500/20 text-amber-300 border-amber-500/40 shadow-sm";

          const stLabel =
            st === "closed"
              ? "Chiuso"
              : st === "resolved"
              ? "Risolto"
              : st === "in_progress"
              ? "In Lavorazione"
              : "Aperto";

          return (
            <div className="mt-3 flex items-center justify-between rounded-xl border border-primary/40 bg-primary/10 backdrop-blur-md p-3 text-xs shadow-md">
              <div className="flex items-center gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/20 text-primary shrink-0">
                  <Wrench className="h-4 w-4" />
                </div>
                <div>
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-foreground">Ticket di Supporto Assegnato:</span>
                    <code className="font-mono text-primary font-bold bg-primary/15 px-2 py-0.5 rounded">
                      {activeTicket.ticket_id}
                    </code>
                    <span className={`rounded-full border px-2 py-0.5 text-[10px] uppercase font-semibold ${stColor}`}>
                      {stLabel}
                    </span>
                  </div>
                  <p className="text-[11px] text-muted-foreground mt-0.5">
                    La richiesta è stata presa in carico dal Service Desk. Puoi continuare a scrivere qui per fornire ulteriori dettagli al tecnico.
                  </p>
                </div>
              </div>
            </div>
          );
        })()}


        {/* Messages Stream */}
        <div className="mt-4 flex-1 min-h-0 overflow-y-auto space-y-4 pr-2 custom-scrollbar">
          {!detail ? (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
              Seleziona una conversazione dall&apos;elenco per visualizzare i messaggi.
            </div>
          ) : !detail.messages || detail.messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-xs text-muted-foreground p-8">
              <Sparkles className="h-8 w-8 text-primary/60" />
              <p className="font-medium text-foreground text-sm">Assistente IT Pronto all&apos;uso</p>
              <p className="max-w-md">
                Invia un messaggio per richiedere supporto informatico aziendale (ad es. accesso posta elettronica, configurazione VPN, reset password o problemi di rete).
              </p>
            </div>
          ) : (
            detail.messages.map((msg) => {
              const isAssistant = msg.role === "assistant";
              const sources = msg.metadata_json?.sources as KBSourceItem[] | undefined;
              const hasSources = Boolean(sources && sources.length > 0);
              const isSourcesExpanded = Boolean(expandedSources[msg.id]);
              const phase = msg.metadata_json?.phase;
              const escalationRequested = msg.metadata_json?.escalation_requested;

              if (isAssistant) {
                return (
                  <div key={msg.id} className="flex flex-col items-start gap-1.5 max-w-[90%]">
                    <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                      <div className="flex items-center gap-1 font-semibold text-primary">
                        <Bot className="h-3.5 w-3.5" />
                        <span>Assistente Service Desk</span>
                      </div>
                      {phase && (
                        <span className="rounded bg-primary/10 border border-primary/20 px-1.5 py-0.2 text-[10px] font-medium text-primary uppercase">
                          {phase}
                        </span>
                      )}
                      <span>•</span>
                      <span>
                        {new Date(msg.created_at).toLocaleTimeString([], {
                          hour: "2-digit",
                          minute: "2-digit",
                          second: "2-digit",
                        })}
                      </span>
                    </div>

                    <div className="w-full rounded-2xl rounded-tl-sm border border-white/10 bg-card/80 p-4 shadow-md backdrop-blur-md">
                      <MarkdownMessage content={msg.content} />

                      {/* Escalation Pill */}
                      {escalationRequested && (
                        <div className="mt-3 flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-1.5 text-xs text-amber-200">
                          <Tag className="h-3.5 w-3.5 text-amber-400" />
                          <span>Richiesta contrassegnata per escalation al team tecnico umano.</span>
                        </div>
                      )}

                      {/* Truncation Warning Pill */}
                      {(msg.metadata_json?.is_truncated || msg.metadata_json?.finish_reason === "MAX_TOKENS") && (
                        <div className="mt-3 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 text-xs text-amber-200">
                          <AlertCircle className="h-4 w-4 text-amber-400 mt-0.5 shrink-0" />
                          <div>
                            <p className="font-semibold text-amber-300">Risposta interrotta per limite token</p>
                            <p className="text-[11px] text-amber-200/80 mt-0.5">
                              L&apos;assistente ha raggiunto la lunghezza massima consentita per questo turno. Invia un messaggio di chiarimento per continuare.
                            </p>
                          </div>
                        </div>
                      )}

                      {/* Cited Sources Collapsible Section */}
                      {hasSources && sources && (
                        <div className="mt-3 pt-3 border-t border-white/10">
                          <button
                            onClick={() => toggleSources(msg.id)}
                            className="inline-flex items-center gap-1.5 text-xs font-semibold text-muted-foreground hover:text-foreground transition-colors"
                          >
                            <BookOpen className="h-3.5 w-3.5 text-primary" />
                            <span>Fonti Knowledge Base consultate ({sources.length})</span>
                            {isSourcesExpanded ? (
                              <ChevronUp className="h-3.5 w-3.5" />
                            ) : (
                              <ChevronDown className="h-3.5 w-3.5" />
                            )}
                          </button>

                          {isSourcesExpanded && (
                            <div className="mt-2 grid grid-cols-1 gap-2">
                              {sources.map((src, sIdx) => (
                                <div
                                  key={sIdx}
                                  className="flex flex-col gap-0.5 rounded-lg border border-white/10 bg-black/20 backdrop-blur-sm p-2 text-xs"
                                >
                                  <div className="flex items-center justify-between">
                                    <span className="font-semibold text-primary">{src.doc_id}</span>
                                    {src.score !== undefined && (
                                      <span className="text-[10px] text-muted-foreground font-mono">
                                        score: {src.score.toFixed(3)}
                                      </span>
                                    )}
                                  </div>
                                  <span className="font-medium text-foreground">{src.title}</span>
                                  {src.heading && (
                                    <span className="text-[11px] text-muted-foreground">
                                      Sezione: {src.heading}
                                    </span>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                );
              }

              // User message bubble
              return (
                <div key={msg.id} className="flex flex-col items-end gap-1 self-end max-w-[85%]">
                  <div className="flex items-center gap-1.5 text-[11px] text-muted-foreground">
                    <User className="h-3 w-3" />
                    <span className="font-semibold text-foreground">Tu (Dipendente)</span>
                    <span>•</span>
                    <span>
                      {new Date(msg.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                  </div>
                  <div className="rounded-2xl rounded-tr-sm bg-primary/95 text-primary-foreground px-4 py-2.5 text-sm font-normal shadow-md backdrop-blur-sm">
                    <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                  </div>
                </div>
              );
            })
          )}

          {/* Thinking / Retrieving State Banner */}
          {(assistantStatus === "thinking" || assistantStatus === "sending") && (
            <div className="flex items-center gap-2.5 rounded-2xl border border-primary/30 bg-primary/10 backdrop-blur-md p-3.5 text-xs text-foreground max-w-[70%] animate-pulse">
              <Bot className="h-4 w-4 text-primary animate-spin" />
              <span>
                {assistantStatus === "sending"
                  ? "Salvataggio messaggio..."
                  : "Assistente IT sta consultando la Knowledge Base ed elaborando la risposta..."}
              </span>
            </div>
          )}

          {/* Assistant Error Notification with Retry */}
          {assistantStatus === "failed" && assistantError && (
            <div className="flex flex-col gap-2 rounded-2xl border border-destructive/40 bg-destructive/10 backdrop-blur-md p-4 text-xs text-destructive max-w-[85%]">
              <div className="flex items-center gap-2">
                <AlertCircle className="h-4 w-4 shrink-0 text-destructive" />
                <span className="font-semibold">Errore generazione risposta assistente</span>
              </div>
              <p className="text-foreground/90">{assistantError}</p>
              <div>
                <button
                  onClick={handleRetryAssistantTurn}
                  className="inline-flex items-center gap-1.5 rounded-lg bg-destructive px-3 py-1.5 text-xs font-semibold text-destructive-foreground hover:bg-destructive/90 active:scale-95 transition-transform"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  <span>Riprova elaborazione</span>
                </button>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Notice for resolved confirmation */}
        {resolutionNotice && (
          <div className="mt-2 flex items-center justify-between rounded-xl border border-emerald-500/30 bg-emerald-500/10 p-3 text-xs text-emerald-300 shadow-sm shrink-0">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4 shrink-0 text-emerald-400" />
              <span>{resolutionNotice}</span>
            </div>
            <button
              onClick={() => setResolutionNotice(null)}
              className="text-xs text-muted-foreground hover:text-foreground px-1"
            >
              ✕
            </button>
          </div>
        )}

        {/* Bot-Resolved Confirmation Card with Sliding Timer inside the primary button */}
        {isResolutionSuggested && secondsLeft !== null && (
          <div className="mt-2 rounded-2xl border border-emerald-500/40 bg-emerald-950/40 backdrop-blur-md p-3.5 text-xs shadow-lg shrink-0">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div className="flex items-start gap-2.5">
                <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400 shrink-0 mt-0.5">
                  <CheckCircle2 className="h-4 w-4" />
                </div>
                <div>
                  <h3 className="font-bold text-foreground text-sm">
                    L&apos;assistente ritiene che il problema sia stato risolto
                  </h3>
                  <p className="text-muted-foreground mt-0.5 text-xs">
                    Confermi che l&apos;intervento ha risolto la tua problematica?
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-2 shrink-0 self-end sm:self-center">
                {/* Button with integrated sliding animated progress bar */}
                <button
                  type="button"
                  disabled={confirmingResolution}
                  onClick={() => handleConfirmResolution(activeRequest?.id || null, true)}
                  aria-label="Il problema è risolto"
                  className="relative overflow-hidden group inline-flex items-center justify-center rounded-xl bg-emerald-800 hover:bg-emerald-700 text-white font-bold text-xs shadow-md border border-emerald-500/50 active:scale-95 transition-all min-w-[190px] h-9 px-4"
                >
                  {/* Sliding timer progress bar directly inside the button (parte verde chiaro e si riduce da destra verso sinistra) */}
                  <div
                    className="absolute inset-y-0 left-0 bg-emerald-500 transition-all duration-1000 ease-linear pointer-events-none"
                    style={{
                      width: `${Math.max(0, Math.min(100, ((secondsLeft ?? 120) / 120) * 100))}%`,
                    }}
                  />
                  <div className="relative z-10 flex items-center gap-2 drop-shadow-sm">
                    {confirmingResolution ? (
                      <Loader2 className="h-4 w-4 animate-spin text-white" />
                    ) : (
                      <Check className="h-4 w-4 stroke-[2.5] text-white" />
                    )}
                    <span>Il problema è risolto</span>
                  </div>
                </button>

                <button
                  type="button"
                  disabled={confirmingResolution}
                  onClick={() => handleContinueConversation(activeRequest?.id || null)}
                  aria-label="Continua conversazione"
                  className="inline-flex items-center gap-1.5 rounded-xl border border-white/20 bg-white/5 hover:bg-white/10 px-3.5 h-9 text-xs font-semibold text-foreground active:scale-95 transition-all"
                >
                  <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
                  <span>Continua conversazione</span>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Message Input Form or Resolved Conversation Banner */}
        {detail && isConversationResolved ? (
          <div className="mt-3 flex flex-col sm:flex-row items-center justify-between gap-3 rounded-2xl border border-emerald-500/30 bg-emerald-950/30 backdrop-blur-md p-3.5 text-xs text-foreground shrink-0 shadow-md">
            <div className="flex items-center gap-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400 shrink-0">
                <CheckCircle2 className="h-4 w-4" />
              </div>
              <div>
                <p className="font-bold text-foreground text-sm">
                  Problema risolto — Conversazione conclusa
                </p>
                <p className="text-muted-foreground text-[11px] mt-0.5">
                  La richiesta è stata chiusa con successo. Non è più possibile inviare messaggi in questo thread.
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={handleCreateNewThread}
              className="inline-flex items-center gap-1.5 rounded-xl bg-primary hover:bg-primary-hover px-3.5 py-2 text-xs font-semibold text-primary-foreground shadow-md active:scale-95 transition-all shrink-0"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Nuova Richiesta</span>
            </button>
          </div>
        ) : (
          detail && (
            <form onSubmit={handleSendMessage} className="mt-3 flex gap-2 pt-3 border-t border-white/10 shrink-0">
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                disabled={assistantStatus !== "ready"}
                placeholder="Descrivi il tuo problema IT (es. Non riesco ad accedere alla casella di posta)..."
                className="flex-1 rounded-xl border border-white/15 bg-background/70 backdrop-blur-md px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none disabled:opacity-50 transition-colors"
              />
              <button
                type="submit"
                disabled={assistantStatus !== "ready" || !inputText.trim()}
                aria-label="Invia Messaggio"
                className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary-hover active:scale-95 transition-transform disabled:opacity-50 disabled:pointer-events-none shadow-md"
              >
                {assistantStatus !== "ready" ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <>
                    <Send className="h-4 w-4" />
                    <span className="hidden sm:inline">Invia</span>
                  </>
                )}
              </button>
            </form>
          )
        )}
      </div>

      {/* Modal for SupportRequest registration */}
      {selectedId && (
        <NewRequestModal
          conversationId={selectedId}
          isOpen={isModalOpen}
          onClose={() => setIsModalOpen(false)}
          onSubmit={handleCreateSupportRequest}
        />
      )}
    </section>
  );
};
