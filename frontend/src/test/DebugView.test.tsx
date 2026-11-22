import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DebugView } from "../components/DebugView";
import type { AuditConversationsResponse, AuditEventsResponse } from "../types/api";

const mockAuditEvents: AuditEventsResponse = {
  items: [
    {
      id: "evt_001",
      event_type: "conversation_created",
      category: "employee",
      action_label: "Apertura nuova chat",
      conversation_id: "conv_test_123",
      request_id: null,
      ticket_id: null,
      payload: { user_id: "user_demo_01", title: "Problema stampante" },
      created_at: "2026-11-22T10:00:00Z",
    },
    {
      id: "evt_002",
      event_type: "assistant_turn_completed",
      category: "employee",
      action_label: "Risposta Assistente Dipendenti (AI)",
      conversation_id: "conv_test_123",
      request_id: "req_001",
      ticket_id: null,
      payload: {
        latency_ms: 1250,
        tokens: {
          prompt_tokens: 450,
          thoughts_tokens: 300,
          completion_tokens: 150,
          total_tokens: 900,
        },
        finish_reason: "STOP",
        is_truncated: false,
      },
      created_at: "2026-11-22T10:01:00Z",
    },
    {
      id: "evt_003",
      event_type: "ticket_created",
      category: "technician",
      action_label: "Ticket IT creato (Escalation)",
      conversation_id: "conv_test_123",
      request_id: "req_001",
      ticket_id: "tick_abc_99",
      payload: {
        ticket_id: "tick_abc_99",
        priority: "medium",
        summary_quality: "llm",
      },
      created_at: "2026-11-22T10:02:00Z",
    },
  ],
  total: 3,
  limit: 100,
  offset: 0,
};

const mockAuditConversations: AuditConversationsResponse = {
  items: [
    {
      conversation_id: "conv_test_123",
      title: "Problema stampante",
      user_id: "user_demo_01",
      status: "active",
      event_count: 3,
      ticket_id: "tick_abc_99",
      ticket_status: "open",
      created_at: "2026-11-22T10:00:00Z",
      updated_at: "2026-11-22T10:02:00Z",
    },
  ],
  total: 1,
};

describe("DebugView component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/api/audit/events")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => mockAuditEvents,
        });
      }
      if (url.includes("/api/audit/conversations")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => mockAuditConversations,
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({}),
      });
    });
  });

  it("renders header, controls, and event list", async () => {
    render(<DebugView />);

    expect(
      screen.getByText("Console Live Debug & Audit Eventi")
    ).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Apertura nuova chat")).toBeInTheDocument();
      expect(screen.getByText("Risposta Assistente Dipendenti (AI)")).toBeInTheDocument();
      expect(screen.getByText("Ticket IT creato (Escalation)")).toBeInTheDocument();
    });

    // Verify token and latency pills
    expect(screen.getByText(/900 tok/i)).toBeInTheDocument();
    expect(screen.getByText(/1250 ms/i)).toBeInTheDocument();
  });

  it("expands event card to show full JSON payload and token breakdown", async () => {
    render(<DebugView />);

    await waitFor(() => {
      expect(screen.getByText("Risposta Assistente Dipendenti (AI)")).toBeInTheDocument();
    });

    // Click on the assistant event row to expand
    const assistantRow = screen.getByText("Risposta Assistente Dipendenti (AI)");
    fireEvent.click(assistantRow);

    // Verify expanded details are visible
    await waitFor(() => {
      expect(screen.getByText("Prompt Tokens")).toBeInTheDocument();
      expect(screen.getByText("Thinking / Reasoning")).toBeInTheDocument();
      expect(screen.getByText("Payload Audit Completo (JSON)")).toBeInTheDocument();
    });
  });

  it("filters events by search query", async () => {
    render(<DebugView />);

    await waitFor(() => {
      expect(screen.getByText("Apertura nuova chat")).toBeInTheDocument();
    });

    const searchInput = screen.getByPlaceholderText(/Cerca evento/i);
    fireEvent.change(searchInput, { target: { value: "ticket_created" } });

    expect(screen.getByText("Ticket IT creato (Escalation)")).toBeInTheDocument();
    expect(screen.queryByText("Apertura nuova chat")).not.toBeInTheDocument();
  });

  it("toggles auto-refresh state", async () => {
    render(<DebugView />);

    const liveBtn = screen.getByText(/Live Attivo/i);
    fireEvent.click(liveBtn);

    expect(screen.getByText(/Live In Pausa/i)).toBeInTheDocument();

    fireEvent.click(screen.getByText(/Live In Pausa/i));
    expect(screen.getByText(/Live Attivo/i)).toBeInTheDocument();
  });
});
