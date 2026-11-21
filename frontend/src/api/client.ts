import type {
  ConversationDetail,
  ConversationListResponse,
  MessageItem,
  SupportRequestItem,
  SupportRequestListResponse,
} from "../types/api";

const API_BASE = "/api";

export async function getConversations(limit: number = 50, offset: number = 0): Promise<ConversationListResponse> {
  const res = await fetch(`${API_BASE}/conversations?limit=${limit}&offset=${offset}`);
  if (!res.ok) {
    throw new Error(`Errore recupero conversazioni (${res.status})`);
  }
  return res.json();
}

export async function createConversation(title?: string): Promise<ConversationDetail> {
  const res = await fetch(`${API_BASE}/conversations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: title || "Nuova Richiesta IT" }),
  });
  if (!res.ok) {
    throw new Error(`Errore creazione conversazione (${res.status})`);
  }
  return res.json();
}

export async function getConversation(conversationId: string): Promise<ConversationDetail> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}`);
  if (!res.ok) {
    throw new Error(`Conversazione non trovata (${res.status})`);
  }
  return res.json();
}

export async function sendMessage(conversationId: string, content: string): Promise<MessageItem> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore invio messaggio (${res.status})`);
  }
  return res.json();
}

export async function createSupportRequest(
  conversationId: string,
  title: string,
  description: string,
  initialCategory?: string
): Promise<SupportRequestItem> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      title,
      description,
      initial_category: initialCategory || null,
    }),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore registrazione richiesta (${res.status})`);
  }
  return res.json();
}

export async function getSupportRequests(
  statusFilter?: string,
  limit: number = 50,
  offset: number = 0
): Promise<SupportRequestListResponse> {
  const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
  if (statusFilter && statusFilter !== "all") {
    params.set("status", statusFilter);
  }
  const res = await fetch(`${API_BASE}/requests?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Errore recupero richieste IT (${res.status})`);
  }
  return res.json();
}
