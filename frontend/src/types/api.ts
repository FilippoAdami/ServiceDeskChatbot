export interface HealthResponse {
  status: "ok" | "error" | string;
  database: "connected" | "disconnected" | string;
  timestamp: string;
  version: string;
  environment: string;
  detail?: string | null;
}
