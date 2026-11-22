import type {
  AssistantTurnResponse,
  ConversationDetail,
  ConversationListResponse,
  IncidentDetail,
  IncidentListResponse,
  MessageItem,
  SupportRequestItem,
  SupportRequestListResponse,
  TicketActivityItem,
  TicketDetail,
  TicketListResponse,
  TechnicianChatMessage,
  TechnicianChatTurnResponse,
  KnowledgeProposal,
  KnowledgeProposalListResponse,
  DuplicateCandidate,
  KnowledgeProposalUpdateRequest,
  KnowledgeProposalApproveRequest,
  AuditCategory,
  AuditEventsResponse,
  AuditConversationsResponse,
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

export async function triggerAssistantTurn(conversationId: string): Promise<AssistantTurnResponse> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/assistant-turn`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore elaborazione assistente (${res.status})`);
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

export async function confirmSupportRequestResolution(
  requestId: string,
  confirmedByUser: boolean = true
): Promise<SupportRequestItem> {
  const res = await fetch(`${API_BASE}/requests/${requestId}/confirm-resolution`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirmed_by_user: confirmedByUser }),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore conferma risoluzione (${res.status})`);
  }
  return res.json();
}

export async function confirmConversationResolution(
  conversationId: string,
  confirmedByUser: boolean = true
): Promise<SupportRequestItem> {
  const res = await fetch(`${API_BASE}/conversations/${conversationId}/confirm-resolution`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ confirmed_by_user: confirmedByUser }),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore conferma risoluzione (${res.status})`);
  }
  return res.json();
}

export async function reopenSupportRequest(

  requestId: string
): Promise<SupportRequestItem> {
  const res = await fetch(`${API_BASE}/requests/${requestId}/reopen`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore riapertura richiesta (${res.status})`);
  }
  return res.json();
}




export async function getTickets(
  statusFilter?: string,
  categoryFilter?: string,
  incidentId?: string,
  limit: number = 50,
  offset: number = 0
): Promise<TicketListResponse> {
  const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
  if (statusFilter && statusFilter !== "all") {
    params.set("status", statusFilter);
  }
  if (categoryFilter && categoryFilter !== "all") {
    params.set("category", categoryFilter);
  }
  if (incidentId) {
    params.set("incident_id", incidentId);
  }
  const res = await fetch(`${API_BASE}/tickets?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Errore recupero ticket (${res.status})`);
  }
  return res.json();
}

export async function getTicket(ticketId: string): Promise<TicketDetail> {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}`);
  if (!res.ok) {
    throw new Error(`Ticket '${ticketId}' non trovato (${res.status})`);
  }
  return res.json();
}

export async function updateTicketStatus(
  ticketId: string,
  status: string,
  note?: string,
  author: string = "technician_demo"
): Promise<TicketDetail> {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}/status`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ status, note, author }),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Transizione stato non valida (${res.status})`);
  }
  return res.json();
}

export async function addTicketNote(
  ticketId: string,
  content: string,
  author: string = "technician_demo"
): Promise<TicketActivityItem> {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}/notes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, author }),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore inserimento nota (${res.status})`);
  }
  return res.json();
}

export async function linkTicketIncident(
  ticketId: string,
  incidentId: string | null,
  author: string = "technician_demo"
): Promise<TicketDetail> {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}/incident`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ incident_id: incidentId, author }),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore collegamento incidente (${res.status})`);
  }
  return res.json();
}

export async function getIncidents(
  statusFilter?: string,
  service?: string
): Promise<IncidentListResponse> {
  const params = new URLSearchParams();
  if (statusFilter && statusFilter !== "all") {
    params.set("status", statusFilter);
  }
  if (service) {
    params.set("service", service);
  }
  const url = params.toString() ? `${API_BASE}/incidents?${params.toString()}` : `${API_BASE}/incidents`;
  const res = await fetch(url);
  if (!res.ok) {
    throw new Error(`Errore recupero incidenti (${res.status})`);
  }
  return res.json();
}

export async function getIncident(incidentId: string): Promise<IncidentDetail> {
  const res = await fetch(`${API_BASE}/incidents/${incidentId}`);
  if (!res.ok) {
    throw new Error(`Incidente '${incidentId}' non trovato (${res.status})`);
  }
  return res.json();
}

// Technician AI Assistant Chat APIs
export async function getTicketChat(ticketId: string): Promise<TechnicianChatMessage[]> {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}/chat`);
  if (!res.ok) {
    throw new Error(`Errore recupero chat tecnico (${res.status})`);
  }
  return res.json();
}

export async function sendTicketChatMessage(
  ticketId: string,
  content: string,
  author: string = "technician_demo"
): Promise<TechnicianChatTurnResponse> {
  const res = await fetch(`${API_BASE}/tickets/${ticketId}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content, author }),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore invio messaggio assistente tecnico (${res.status})`);
  }
  return res.json();
}

// Knowledge Base Proposal Management APIs
export async function getKnowledgeProposals(
  statusFilter?: string,
  sourceType?: string,
  limit: number = 50,
  offset: number = 0
): Promise<KnowledgeProposalListResponse> {
  const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
  if (statusFilter && statusFilter !== "all") {
    params.set("status", statusFilter);
  }
  if (sourceType) {
    params.set("source_type", sourceType);
  }
  const res = await fetch(`${API_BASE}/kb-proposals?${params.toString()}`);
  if (!res.ok) {
    throw new Error(`Errore recupero proposte KB (${res.status})`);
  }
  return res.json();
}

export async function getKnowledgeProposal(proposalId: string): Promise<KnowledgeProposal> {
  const res = await fetch(`${API_BASE}/kb-proposals/${proposalId}`);
  if (!res.ok) {
    throw new Error(`Proposta KB '${proposalId}' non trovata (${res.status})`);
  }
  return res.json();
}

export async function generateKnowledgeProposal(
  sourceType: string,
  sourceId: string,
  author: string = "technician_demo"
): Promise<KnowledgeProposal> {
  const res = await fetch(`${API_BASE}/kb-proposals/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source_type: sourceType, source_id: sourceId, author }),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore generazione proposta KB (${res.status})`);
  }
  return res.json();
}

export async function updateKnowledgeProposal(
  proposalId: string,
  payload: KnowledgeProposalUpdateRequest
): Promise<KnowledgeProposal> {
  const res = await fetch(`${API_BASE}/kb-proposals/${proposalId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore aggiornamento proposta KB (${res.status})`);
  }
  return res.json();
}

export async function rejectKnowledgeProposal(
  proposalId: string,
  reason?: string,
  author: string = "technician_demo"
): Promise<KnowledgeProposal> {
  const res = await fetch(`${API_BASE}/kb-proposals/${proposalId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason || "Non applicabile", author }),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore rifiuto proposta KB (${res.status})`);
  }
  return res.json();
}

export async function publishKnowledgeProposal(
  proposalId: string,
  payload: KnowledgeProposalApproveRequest
): Promise<KnowledgeProposal> {
  const res = await fetch(`${API_BASE}/kb-proposals/${proposalId}/publish`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore pubblicazione articolo KB (${res.status})`);
  }
  return res.json();
}

export async function getKnowledgeProposalDuplicates(
  proposalId: string,
  limit: number = 5
): Promise<DuplicateCandidate[]> {
  const res = await fetch(`${API_BASE}/kb-proposals/${proposalId}/duplicates?limit=${limit}`);
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore verifica duplicati KB (${res.status})`);
  }
  return res.json();
}

export async function getAuditEvents(params?: {
  category?: AuditCategory;
  conversation_id?: string;
  event_type?: string;
  limit?: number;
  offset?: number;
}): Promise<AuditEventsResponse> {
  const query = new URLSearchParams();
  if (params?.category && params.category !== "all") {
    query.set("category", params.category);
  }
  if (params?.conversation_id && params.conversation_id !== "all") {
    query.set("conversation_id", params.conversation_id);
  }
  if (params?.event_type) {
    query.set("event_type", params.event_type);
  }
  if (params?.limit) {
    query.set("limit", String(params.limit));
  }
  if (params?.offset) {
    query.set("offset", String(params.offset));
  }
  const queryString = query.toString();
  const url = `${API_BASE}/audit/events${queryString ? `?${queryString}` : ""}`;
  const res = await fetch(url);
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore recupero log di audit (${res.status})`);
  }
  return res.json();
}

export async function getAuditConversations(
  limit: number = 50,
  offset: number = 0
): Promise<AuditConversationsResponse> {
  const res = await fetch(`${API_BASE}/audit/conversations?limit=${limit}&offset=${offset}`);
  if (!res.ok) {
    const errorJson = await res.json().catch(() => ({}));
    throw new Error(errorJson.detail || `Errore recupero conversazioni audit (${res.status})`);
  }
  return res.json();
}

