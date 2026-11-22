export interface HealthResponse {
  status: "ok" | "error" | string;
  database: "connected" | "disconnected" | string;
  gemini_configured?: boolean;
  timestamp: string;
  version: string;
  environment: string;
  detail?: string | null;
}

export interface ConversationSummary {
  id: string;
  user_id: string;
  title: string | null;
  category?: string | null;
  status: "active" | "waiting_user" | "archived" | string;
  created_at: string;
  updated_at: string;
  message_count: number;
  request_count: number;
}

export interface KBSourceItem {
  doc_id: string;
  title: string;
  heading?: string;
  score?: number;
  source_path?: string;
}

export interface MessageMetadata {
  sources?: KBSourceItem[];
  phase?: string;
  escalation_requested?: boolean;
  resolution_proposed?: boolean;
  request_id?: string | null;
  ticket_id?: string | null;
  ticket_status?: string | null;
  summary_quality?: string | null;
  tokens?: Record<string, number>;
  latency_ms?: number;
  model?: string;
  finish_reason?: string | null;
  is_truncated?: boolean;
}




export interface MessageItem {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system" | string;
  content: string;
  metadata_json?: MessageMetadata | null;
  created_at: string;
}

export interface SupportRequestItem {
  id: string;
  conversation_id: string;
  title: string;
  description: string;
  initial_category: string | null;
  final_category: string | null;
  status: "open" | "in_progress" | "closed" | string;
  outcome: string | null;
  phase?: string;
  escalation_requested?: boolean;
  created_at: string;
  updated_at: string;
}

export interface AssistantTurnResponse {
  message: MessageItem;
  sources: KBSourceItem[];
  phase: string;
  escalation_requested: boolean;
  resolution_proposed?: boolean;
  request_id?: string | null;
  tokens: Record<string, number>;
  latency_ms: number;
  finish_reason?: string | null;
  is_truncated?: boolean;
}



export interface ConversationDetail {
  id: string;
  user_id: string;
  title: string | null;
  category?: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  messages: MessageItem[];
  requests: SupportRequestItem[];
}

export interface ConversationListResponse {
  items: ConversationSummary[];
  total: number;
  limit: number;
  offset: number;
}

export interface SupportRequestListResponse {
  items: SupportRequestItem[];
  total: number;
  limit: number;
  offset: number;
}

export type TicketStatus = "open" | "in_progress" | "resolved" | "closed";
export type TicketPriority = "low" | "medium" | "high" | "critical";

export interface TicketActivityItem {
  id: string;
  ticket_id: string;
  author: string;
  author_role: string;
  activity_type: string;
  content: string;
  old_status?: string | null;
  new_status?: string | null;
  created_at: string;
}

export const TASK_CATEGORIES = [
  "Reset Password",
  "Problemi Email",
  "Malfunzionamenti Software",
  "Richiesta Generica",
] as const;

export type TaskCategoryType = (typeof TASK_CATEGORIES)[number];

export interface TicketItem {
  id: string;
  support_request_id: string;
  conversation_id: string;
  incident_id?: string | null;
  category?: string | null;
  status: TicketStatus;
  priority: TicketPriority;
  title: string;
  summary: string;
  summary_quality: "llm" | "fallback" | string;
  created_at: string;
  updated_at: string;
}

export interface TicketDetail extends TicketItem {
  symptoms: string;
  attempted_steps: string;
  diagnostic_findings: string;
  source_refs?: string[];
  activities: TicketActivityItem[];
}

export interface TicketListResponse {
  items: TicketItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface IncidentItem {
  id: string;
  service: string;
  title: string;
  symptoms: string;
  summary: string;
  status: "investigating" | "identified" | "monitoring" | "resolved" | string;
  created_at: string;
  updated_at: string;
  ticket_count: number;
}

export interface IncidentDetail extends IncidentItem {
  tickets: TicketItem[];
}

export interface IncidentListResponse {
  items: IncidentItem[];
  total: number;
}

// Operational proposals from the AI technician assistant
export interface OperationalProposals {
  proposed_status?: TicketStatus | null;
  proposed_note?: string | null;
  proposed_cause?: string | null;
  proposed_solution?: string | null;
}

export interface TechnicianChatMessage {
  id: string;
  ticket_id: string;
  author_type: "technician" | "assistant";
  author_name: string;
  content: string;
  operational_proposals?: OperationalProposals | null;
  created_at: string;
}

export interface TechnicianChatTurnResponse {
  assistant_message: TechnicianChatMessage;
}

export type ProposalStatus = "draft" | "under_review" | "approved" | "rejected" | "publishing_failed";
export type ProposalSourceType = "support_request" | "ticket";
export type ProposalDestination = "new_document" | "update_existing";

export interface KnowledgeProposal {
  id: string;
  source_type: ProposalSourceType;
  source_id: string;
  status: ProposalStatus;
  destination: ProposalDestination;
  target_kb_slug?: string | null;
  target_doc_id?: string | null;
  title: string;
  content_markdown: string;
  generated_category?: string | null;
  review_notes?: string | null;
  rejection_reason?: string | null;
  author: string;
  reviewer?: string | null;
  published_path?: string | null;
  published_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface KnowledgeProposalListResponse {
  items: KnowledgeProposal[];
  total: number;
  limit: number;
  offset: number;
}

export interface DuplicateCandidate {
  slug: string;
  doc_id: string;
  title: string;
  category: string;
  similarity: number;
  preview: string;
  score?: number;
  source_path?: string;
  summary?: string;
}

export interface KnowledgeProposalUpdateRequest {
  title?: string;
  content_markdown?: string;
  destination?: ProposalDestination;
  target_kb_slug?: string | null;
  notes?: string | null;
}

export interface KnowledgeProposalApproveRequest {
  destination?: ProposalDestination;
  target_kb_slug?: string | null;
  author?: string;
}

export type AuditCategory = "all" | "employee" | "technician" | "system";

export interface AuditEventItem {
  id: string;
  event_type: string;
  category: "employee" | "technician" | "system";
  action_label: string;
  conversation_id?: string | null;
  request_id?: string | null;
  ticket_id?: string | null;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface AuditEventsResponse {
  items: AuditEventItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface AuditConversationSummary {
  conversation_id: string;
  title: string;
  user_id: string;
  status: string;
  event_count: number;
  ticket_id?: string | null;
  ticket_status?: string | null;
  created_at: string;
  updated_at: string;
}

export interface AuditConversationsResponse {
  items: AuditConversationSummary[];
  total: number;
}

