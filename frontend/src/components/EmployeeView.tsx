import React, { useEffect, useState, useCallback, useRef } from "react";
import {
  MessageSquare,
  Plus,
  Send,
  FilePlus,
  Info,
  Clock,
  User,
  AlertCircle,
  Loader2,
  Tag,
} from "lucide-react";
import type { ConversationDetail, ConversationSummary } from "../types/api";
import {
  createConversation,
  createSupportRequest,
  getConversation,
  getConversations,
  sendMessage,
} from "../api/client";
import { NewRequestModal } from "./NewRequestModal";

export const EmployeeView: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ConversationDetail | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [sending, setSending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [inputText, setInputText] = useState<string>("");
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    if (typeof messagesEndRef.current?.scrollIntoView === "function") {
      messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  };

  const loadConversations = useCallback(async (selectNewestId?: string) => {
    try {
      setLoading(true);
      setError(null);
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
        setError(err.message);
      } else {
        setError("Impossibile caricare le conversazioni");
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
  }, [detail?.messages]);

  const handleSelectConversation = async (id: string) => {
    try {
      setSelectedId(id);
      setError(null);
      const detailData = await getConversation(id);
      setDetail(detailData);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    }
  };

  const handleCreateNewThread = async () => {
    try {
      setLoading(true);
      setError(null);
      const newConv = await createConversation("Nuova Richiesta IT");
      await loadConversations(newConv.id);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || !selectedId || sending) return;

    const content = inputText.trim();
    try {
      setSending(true);
      setError(null);
      const savedMsg = await sendMessage(selectedId, content);
      setInputText("");

      // Update current detail state with the new message
      setDetail((prev) => {
        if (!prev) return null;
        return {
          ...prev,
          updated_at: savedMsg.created_at,
          messages: [...prev.messages, savedMsg],
        };
      });

      // Refresh list to update message counter and order
      const listData = await getConversations(50, 0);
      setConversations(listData.items);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      }
    } finally {
      setSending(false);
    }
  };

  const handleCreateSupportRequest = async (
    title: string,
    description: string,
    category: string
  ) => {
    if (!selectedId) return;
    const newReq = await createSupportRequest(selectedId, title, description, category);

    // Update current detail state with new request
    setDetail((prev) => {
      if (!prev) return null;
      return {
        ...prev,
        requests: [newReq, ...prev.requests],
      };
    });

    // Refresh conversations list to update count
    const listData = await getConversations(50, 0);
    setConversations(listData.items);
  };

  return (
    <section
      id="panel-employee"
      role="tabpanel"
      aria-labelledby="tab-employee"
      className="grid grid-cols-1 gap-6 lg:grid-cols-12"
    >
      {/* Sidebar: Conversation Threads */}
      <div className="flex flex-col rounded-2xl border border-border bg-card p-4 shadow-sm lg:col-span-4 lg:h-[750px]">
        <div className="flex items-center justify-between pb-4 border-b border-border/80">
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
        <div className="mt-3 flex-1 overflow-y-auto space-y-2 pr-1">
          {loading && conversations.length === 0 ? (
            <div className="flex items-center justify-center p-8 text-xs text-muted-foreground">
              <Loader2 className="h-5 w-5 animate-spin mr-2 text-primary" />
              <span>Caricamento conversazioni...</span>
            </div>
          ) : conversations.length === 0 ? (
            <div className="rounded-xl border border-dashed border-border p-6 text-center text-xs text-muted-foreground">
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
                      ? "border-primary bg-primary/10 shadow-sm"
                      : "border-border/60 bg-background/50 hover:bg-background/80"
                  }`}
                >
                  <div className="flex items-center justify-between font-semibold text-foreground">
                    <span className="truncate max-w-[190px]">
                      {conv.title || "Richiesta IT"}
                    </span>
                    <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {new Date(conv.updated_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                  </div>
                  <div className="mt-2 flex items-center gap-2 text-[11px] text-muted-foreground">
                    <span>{conv.message_count} messaggi</span>
                    {conv.request_count > 0 && (
                      <span className="rounded bg-accent px-1.5 py-0.5 text-[10px] text-accent-foreground font-medium">
                        {conv.request_count} problemi IT
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
      <div className="flex flex-col rounded-2xl border border-border bg-card p-4 shadow-sm lg:col-span-8 lg:h-[750px]">
        {/* Thread Header */}
        <div className="flex flex-col gap-2 pb-4 border-b border-border/80 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-foreground">
                {detail?.title || "Seleziona o crea una conversazione"}
              </h2>
              {detail && (
                <span className="rounded-md bg-secondary px-2 py-0.5 text-[10px] font-semibold text-muted-foreground uppercase">
                  {detail.status}
                </span>
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

        {/* Global Notice (Strict invariant from GOAL_02) */}
        <div className="mt-3 flex items-start gap-2 rounded-xl border border-primary/20 bg-primary/5 p-3 text-xs text-foreground">
          <Info className="h-4 w-4 shrink-0 text-primary mt-0.5" />
          <p className="leading-relaxed">
            <strong>Assistente AI non attivo in questa versione (Milestone G02):</strong> I messaggi
            dell&apos;utente vengono sanitizzati da segreti e salvati persistentemente in SQLite. Nessuna
            risposta simulata viene generata. Le risposte reali dell&apos;agente Gemini saranno introdotte in G04.
          </p>
        </div>

        {/* Error notification */}
        {error && (
          <div className="mt-3 flex items-center gap-2 rounded-xl border border-destructive/40 bg-destructive/10 p-3 text-xs text-destructive">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {/* Registered Requests Pill Header */}
        {detail && detail.requests && detail.requests.length > 0 && (
          <div className="mt-3 space-y-1.5">
            <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
              Richieste IT associate a questo thread:
            </span>
            <div className="flex flex-wrap gap-2">
              {detail.requests.map((req) => (
                <div
                  key={req.id}
                  className="inline-flex items-center gap-1.5 rounded-lg border border-border bg-background px-2.5 py-1 text-xs"
                >
                  <Tag className="h-3 w-3 text-primary" />
                  <span className="font-medium text-foreground">{req.title}</span>
                  <span className="rounded bg-secondary px-1 text-[10px] text-muted-foreground uppercase">
                    {req.status}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Messages Stream */}
        <div className="mt-4 flex-1 overflow-y-auto space-y-3 pr-2">
          {!detail ? (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
              Seleziona una conversazione dall&apos;elenco per visualizzare i messaggi.
            </div>
          ) : !detail.messages || detail.messages.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-xs text-muted-foreground p-8">
              <MessageSquare className="h-8 w-8 text-muted-foreground/50" />
              <p className="font-medium text-foreground">Nessun messaggio in questo thread.</p>
              <p>Invia il primo messaggio descrivendo il problema IT riscontrato.</p>
            </div>
          ) : (
            detail.messages.map((msg) => (
              <div
                key={msg.id}
                className="flex flex-col items-end gap-1"
              >
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
                <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-primary px-4 py-2.5 text-sm font-normal text-primary-foreground shadow-sm">
                  <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Message Input Form */}
        {detail && (
          <form onSubmit={handleSendMessage} className="mt-4 flex gap-2 pt-3 border-t border-border/80">
            <input
              type="text"
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              disabled={sending}
              placeholder="Descrivi il tuo problema IT (es. Non riesco ad accedere alla casella di posta)..."
              className="flex-1 rounded-xl border border-input bg-background px-4 py-2.5 text-sm text-foreground placeholder:text-muted-foreground focus:border-primary focus:outline-none"
            />
            <button
              type="submit"
              disabled={sending || !inputText.trim()}
              aria-label="Invia Messaggio"
              className="inline-flex items-center gap-2 rounded-xl bg-primary px-4 py-2.5 text-sm font-semibold text-primary-foreground hover:bg-primary-hover active:scale-95 transition-transform disabled:opacity-50 disabled:pointer-events-none"
            >
              {sending ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  <span className="hidden sm:inline">Invia</span>
                </>
              )}
            </button>
          </form>
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
