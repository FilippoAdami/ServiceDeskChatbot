import React, { useEffect, useState, useRef, useCallback } from "react";
import {
  Bot,
  Send,
  Loader2,
  AlertCircle,
  ArrowRight,
  Sparkles,
  BookOpen,
} from "lucide-react";
import type { TechnicianChatMessage, TicketDetail } from "../types/api";
import { getTicketChat, sendTicketChatMessage } from "../api/client";

interface TechnicianChatPanelProps {
  ticket: TicketDetail;
  onApplyProposal?: (proposedStatus?: string | null, proposedNote?: string | null) => Promise<void>;
  onGenerateKBProposal?: () => Promise<void>;
  generatingKB?: boolean;
}

export const TechnicianChatPanel: React.FC<TechnicianChatPanelProps> = ({
  ticket,
  onApplyProposal,
  onGenerateKBProposal,
  generatingKB = false,
}) => {
  const [messages, setMessages] = useState<TechnicianChatMessage[]>([]);
  const [input, setInput] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(true);
  const [sending, setSending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [applyingProposalId, setApplyingProposalId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);

  const loadChat = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const history = await getTicketChat(ticket.id);
      setMessages(Array.isArray(history) ? history : []);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore nel caricamento della chat");
    } finally {
      setLoading(false);
    }
  }, [ticket.id]);

  useEffect(() => {
    loadChat();
  }, [loadChat]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = async (customContent?: string) => {
    const textToSend = customContent || input;
    if (!textToSend.trim() || sending) return;

    try {
      setSending(true);
      setError(null);
      setInput("");
      const response = await sendTicketChatMessage(ticket.id, textToSend, "technician_demo");
      setMessages((prev) => [
        ...prev,
        {
          id: `local-${Date.now()}`,
          ticket_id: ticket.id,
          author_type: "technician",
          author_name: "technician_demo",
          content: textToSend,
          created_at: new Date().toISOString(),
        },
        response.assistant_message,
      ]);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore invio messaggio all'assistente");
    } finally {
      setSending(false);
    }
  };

  const handleApplyOperationalProposal = async (msg: TechnicianChatMessage) => {
    if (!msg.operational_proposals || !onApplyProposal) return;
    try {
      setApplyingProposalId(msg.id);
      setError(null);
      await onApplyProposal(
        msg.operational_proposals.proposed_status,
        msg.operational_proposals.proposed_note
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Errore applicazione proposta");
    } finally {
      setApplyingProposalId(null);
    }
  };

  return (
    <div className="flex flex-col h-full rounded-xl border border-white/10 bg-white/[0.02] shadow-inner overflow-hidden">
      {/* Assistant Header */}
      <div className="p-3 border-b border-white/10 flex items-center justify-between bg-primary/5">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Bot className="h-4 w-4" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold text-foreground">Copilota AI Tecnico</span>
              <span className="rounded bg-primary/20 px-1.5 py-0.2 text-[9px] font-semibold text-primary">
                Gemini + RAG
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground">
              Consulenza su diagnosi, KB e proposte operative non vincolanti
            </p>
          </div>
        </div>

        {onGenerateKBProposal && (
          <button
            onClick={onGenerateKBProposal}
            disabled={generatingKB}
            title="Genera una bozza di articolo per la Knowledge Base da questo ticket"
            className="inline-flex items-center gap-1.5 rounded-lg border border-primary/30 bg-primary/10 px-2.5 py-1 text-[11px] font-semibold text-primary hover:bg-primary/20 active:scale-95 transition-all disabled:opacity-50"
          >
            {generatingKB ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <BookOpen className="h-3 w-3" />
            )}
            <span>Genera Bozza KB</span>
          </button>
        )}
      </div>

      {/* Quick Prompts Bar */}
      <div className="px-3 py-1.5 border-b border-white/5 bg-background/40 flex items-center gap-1.5 overflow-x-auto text-[10px]">
        <span className="text-muted-foreground shrink-0 font-medium">Suggerimenti:</span>
        <button
          onClick={() => handleSend("Quali sono le cause più probabili e i controlli consigliati per questo ticket?")}
          disabled={sending}
          className="rounded border border-white/10 bg-white/5 px-2 py-0.5 text-muted-foreground hover:text-foreground hover:bg-white/10 whitespace-nowrap transition-colors"
        >
          🔍 Cause probabili
        </button>
        <button
          onClick={() => handleSend("C'è un articolo della Knowledge Base applicabile a questo disservizio?")}
          disabled={sending}
          className="rounded border border-white/10 bg-white/5 px-2 py-0.5 text-muted-foreground hover:text-foreground hover:bg-white/10 whitespace-nowrap transition-colors"
        >
          📚 Cerca in KB
        </button>
        <button
          onClick={() => handleSend("Sintetizza una proposta di nota tecnica di risoluzione per il ticket.")}
          disabled={sending}
          className="rounded border border-white/10 bg-white/5 px-2 py-0.5 text-muted-foreground hover:text-foreground hover:bg-white/10 whitespace-nowrap transition-colors"
        >
          📝 Proposta nota risoluzione
        </button>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="mx-3 mt-2 rounded-lg border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-300 flex items-center gap-1.5">
          <AlertCircle className="h-3.5 w-3.5 shrink-0" />
          <span className="flex-1">{error}</span>
          <button onClick={() => setError(null)} className="text-xs hover:underline">
            Chiudi
          </button>
        </div>
      )}

      {/* Messages Thread */}
      <div className="flex-1 min-h-[220px] max-h-[360px] overflow-y-auto p-3 space-y-3 custom-scrollbar">
        {loading ? (
          <div className="flex flex-col items-center justify-center h-full py-8 text-xs text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin text-primary mb-2" />
            <span>Caricamento conversazione assistente...</span>
          </div>
        ) : (!Array.isArray(messages) || messages.length === 0) ? (
          <div className="flex flex-col items-center justify-center h-full py-8 text-center text-xs text-muted-foreground">
            <Sparkles className="h-7 w-7 text-primary/40 mb-2" />
            <p className="font-semibold text-foreground">Nessun messaggio con il copilota per questo ticket</p>
            <p className="text-[11px] max-w-xs mt-1">
              Fai una domanda per richiedere un&apos;analisi delle cause, passaggi di diagnosi o una proposta di nota tecnica.
            </p>
          </div>
        ) : (
          messages.map((msg) => {
            const isAssistant = msg.author_type === "assistant";
            const props = msg.operational_proposals;
            const hasProposals =
              props &&
              (props.proposed_status ||
                props.proposed_note ||
                props.proposed_cause ||
                props.proposed_solution);

            return (
              <div
                key={msg.id}
                className={`flex flex-col ${isAssistant ? "items-start" : "items-end"}`}
              >
                <div
                  className={`max-w-[90%] rounded-2xl p-3 text-xs leading-relaxed shadow-sm ${
                    isAssistant
                      ? "rounded-tl-xs border border-white/10 bg-card/90 text-foreground"
                      : "rounded-tr-xs bg-primary text-primary-foreground font-medium"
                  }`}
                >
                  <div className="flex items-center justify-between gap-2 mb-1 text-[10px] opacity-75">
                    <span className="font-bold flex items-center gap-1">
                      {isAssistant && <Bot className="h-3 w-3" />}
                      {msg.author_name}
                    </span>
                    <span>{new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</span>
                  </div>

                  <p className="whitespace-pre-wrap">{msg.content}</p>

                  {/* Operational Proposals Card (Technician Confirmation Required) */}
                  {isAssistant && hasProposals && (
                    <div className="mt-2.5 pt-2.5 border-t border-white/10 rounded-xl bg-white/[0.04] p-2.5 space-y-2">
                      <div className="flex items-center gap-1.5 text-[11px] font-bold text-primary">
                        <Sparkles className="h-3.5 w-3.5" />
                        <span>Proposta Operativa Suggerita</span>
                      </div>

                      {props.proposed_status && (
                        <div className="text-[11px]">
                          <span className="text-muted-foreground">Stato consigliato: </span>
                          <span className="font-semibold uppercase text-foreground bg-white/10 px-1.5 py-0.5 rounded">
                            {props.proposed_status}
                          </span>
                        </div>
                      )}

                      {props.proposed_cause && (
                        <div className="text-[11px]">
                          <span className="text-muted-foreground">Causa probabile: </span>
                          <span className="text-foreground">{props.proposed_cause}</span>
                        </div>
                      )}

                      {props.proposed_solution && (
                        <div className="text-[11px]">
                          <span className="text-muted-foreground">Soluzione proposta: </span>
                          <span className="text-foreground">{props.proposed_solution}</span>
                        </div>
                      )}

                      {props.proposed_note && (
                        <div className="rounded-lg bg-black/30 p-2 text-[11px] border border-white/5">
                          <span className="font-medium text-muted-foreground block mb-0.5">Nota suggerita:</span>
                          <span className="text-foreground italic">{props.proposed_note}</span>
                        </div>
                      )}

                      {/* Confirmation Button for Technician */}
                      {onApplyProposal && (props.proposed_status || props.proposed_note) && (
                        <div className="pt-1 flex justify-end">
                          <button
                            type="button"
                            disabled={applyingProposalId === msg.id}
                            onClick={() => handleApplyOperationalProposal(msg)}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-primary/20 border border-primary/40 px-2.5 py-1 text-[11px] font-bold text-primary hover:bg-primary/30 active:scale-95 transition-all disabled:opacity-50"
                          >
                            {applyingProposalId === msg.id ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <ArrowRight className="h-3 w-3" />
                            )}
                            <span>Applica Nota e Stato al Ticket</span>
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Form */}
      <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="p-2.5 border-t border-white/10 bg-background/50 flex items-center gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Chiedi al copilota (es. 'Quale procedura KB si applica?')..."
          disabled={sending}
          className="flex-1 rounded-xl border border-white/15 bg-background px-3 py-1.5 text-xs text-foreground focus:outline-none focus:border-primary placeholder:text-muted-foreground/60"
        />
        <button
          type="submit"
          disabled={sending || !input.trim()}
          className="inline-flex items-center justify-center rounded-xl bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary-hover active:scale-95 transition-transform disabled:opacity-50"
        >
          {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
        </button>
      </form>
    </div>
  );
};
