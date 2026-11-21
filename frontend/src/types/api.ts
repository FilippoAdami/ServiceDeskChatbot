export interface HealthResponse {
  status: "ok" | "error" | string;
  database: "connected" | "disconnected" | string;
  timestamp: string;
  version: string;
  environment: string;
  detail?: string | null;
}

export interface ConversationSummary {
  id: string;
  user_id: string;
  title: string | null;
  status: "active" | "waiting_user" | "archived" | string;
  created_at: string;
  updated_at: string;
  message_count: number;
  request_count: number;
}

export interface MessageItem {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system" | string;
  content: string;
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
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail {
  id: string;
  user_id: string;
  title: string | null;
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
