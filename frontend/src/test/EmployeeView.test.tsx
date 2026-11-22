import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { EmployeeView } from "../components/EmployeeView";

describe("EmployeeView component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    // Mock fetch for conversations, messages, assistant turn, health
    global.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      // GET health
      if (url.includes("/api/health")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            status: "ok",
            database: "connected",
            gemini_configured: true,
            timestamp: new Date().toISOString(),
            version: "0.1.0",
            environment: "development",
          }),
        });
      }

      // POST assistant turn
      if (options?.method === "POST" && url.includes("/assistant-turn")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            message: {
              id: "msg_assistant_1",
              conversation_id: "conv_1",
              role: "assistant",
              content: "Ti suggerisco di verificare i parametri di configurazione.",
              metadata_json: {
                sources: [
                  {
                    doc_id: "KB-VPN-001",
                    title: "Risoluzione problemi VPN",
                    heading: "Verifica credenziali",
                    score: 0.88,
                  },
                ],
                phase: "diagnosis",
                escalation_requested: false,
              },
              created_at: new Date().toISOString(),
            },
            sources: [
              {
                doc_id: "KB-VPN-001",
                title: "Risoluzione problemi VPN",
                heading: "Verifica credenziali",
                score: 0.88,
              },
            ],
            phase: "diagnosis",
            escalation_requested: false,
            tokens: { prompt_tokens: 100, completion_tokens: 30, total_tokens: 130 },
            latency_ms: 12.5,
          }),
        });
      }

      // POST message
      if (options?.method === "POST" && url.includes("/messages")) {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: "msg_new",
            conversation_id: "conv_1",
            role: "user",
            content: "Nuovo messaggio inviato",
            created_at: new Date().toISOString(),
          }),
        });
      }

      // POST confirm resolution
      if (options?.method === "POST" && url.includes("/confirm-resolution")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: "req_1",
            conversation_id: "conv_1",
            title: "Problema accesso VPN",
            description: "Dettaglio",
            initial_category: "network",
            status: "closed",
            phase: "finalization",
            outcome: "resolved_confirmed",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
        });
      }

      // POST support request
      if (options?.method === "POST" && url.includes("/requests")) {
        return Promise.resolve({
          ok: true,
          status: 201,
          json: async () => ({
            id: "req_new",
            conversation_id: "conv_1",
            title: "Nuovo ticket",
            description: "Dettaglio problema",
            initial_category: "account",
            status: "open",
            outcome: null,
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
        });
      }


      // GET detail
      if (url.includes("/api/conversations/conv_1")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: "conv_1",
            user_id: "user_demo_01",
            title: "Problema accesso VPN",
            status: "active",
            created_at: "2026-11-21T19:00:00Z",
            updated_at: "2026-11-21T19:00:00Z",
            messages: [
              {
                id: "msg_1",
                conversation_id: "conv_1",
                role: "user",
                content: "Non riesco a connettermi alla VPN",
                created_at: "2026-11-21T19:00:00Z",
              },
            ],
            requests: [],
          }),
        });
      }

      // GET list
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          items: [
            {
              id: "conv_1",
              user_id: "user_demo_01",
              title: "Problema accesso VPN",
              status: "active",
              created_at: "2026-11-21T19:00:00Z",
              updated_at: "2026-11-21T19:00:00Z",
              message_count: 1,
              request_count: 0,
            },
          ],
          total: 1,
          limit: 50,
          offset: 0,
        }),
      });
    });
  });

  it("renders conversation list and initial active thread message", async () => {
    render(<EmployeeView />);

    await waitFor(() => {
      expect(screen.getAllByText("Problema accesso VPN").length).toBeGreaterThanOrEqual(1);
    });

    expect(
      screen.getByText("Non riesco a connettermi alla VPN")
    ).toBeInTheDocument();
  });

  it("allows sending a user message and triggers assistant response with KB sources", async () => {
    render(<EmployeeView />);

    await waitFor(() => {
      expect(screen.getByText("Non riesco a connettermi alla VPN")).toBeInTheDocument();
    });

    const input = screen.getByPlaceholderText(/Descrivi il tuo problema IT/i);
    const sendButton = screen.getByRole("button", { name: /Invia Messaggio/i });

    fireEvent.change(input, { target: { value: "Nuovo messaggio inviato" } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(screen.getByText("Nuovo messaggio inviato")).toBeInTheDocument();
    });

    // Assistant response should appear
    await waitFor(() => {
      expect(
        screen.getByText("Ti suggerisco di verificare i parametri di configurazione.")
      ).toBeInTheDocument();
    });

    // Source button should be present
    expect(
      screen.getByText(/Fonti Knowledge Base consultate \(1\)/i)
    ).toBeInTheDocument();
  });

  it("opens modal to register a SupportRequest", async () => {
    render(<EmployeeView />);

    await waitFor(() => {
      expect(screen.getByText("Segnala Problema IT")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("Segnala Problema IT"));

    expect(screen.getByText("Registra Problema IT (SupportRequest)")).toBeInTheDocument();
    expect(screen.getByLabelText(/Titolo del Problema/i)).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText(/Titolo del Problema/i), {
      target: { value: "Nuovo ticket" },
    });
    fireEvent.change(screen.getByLabelText(/Descrizione Dettagliata/i), {
      target: { value: "Dettaglio problema" },
    });

    fireEvent.click(screen.getByRole("button", { name: /Registra Richiesta/i }));

    await waitFor(() => {
      expect(screen.queryByText("Registra Problema IT (SupportRequest)")).not.toBeInTheDocument();
    });
  });

  it("renders resolution confirmation card with 2-minute timer and confirms on click", async () => {
    global.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.includes("/api/health")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({ status: "ok", database: "connected", gemini_configured: true }),
        });
      }

      if (options?.method === "POST" && url.includes("/confirm-resolution")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: "req_res_1",
            conversation_id: "conv_res",
            title: "Reset password riuscito",
            description: "Dettaglio",
            status: "closed",
            outcome: "resolved_confirmed",
            phase: "finalization",
            created_at: new Date().toISOString(),
            updated_at: new Date().toISOString(),
          }),
        });
      }

      if (url.includes("/api/conversations/conv_res")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            id: "conv_res",
            user_id: "user_demo_01",
            title: "Reset Password",
            status: "active",
            created_at: "2026-11-21T19:00:00Z",
            updated_at: "2026-11-21T19:00:00Z",
            messages: [
              {
                id: "msg_user_1",
                conversation_id: "conv_res",
                role: "user",
                content: "grazie mille sono riuscito ad accedere",
                created_at: "2026-11-21T19:00:00Z",
              },
              {
                id: "msg_assist_1",
                conversation_id: "conv_res",
                role: "assistant",
                content: "Felice di sapere che hai risolto!",
                metadata_json: {
                  phase: "finalization",
                  resolution_proposed: true,
                },
                created_at: "2026-11-21T19:00:05Z",
              },
            ],
            requests: [
              {
                id: "req_res_1",
                conversation_id: "conv_res",
                title: "Reset password account",
                description: "Password dimenticata",
                initial_category: "account",
                status: "open",
                phase: "finalization",
                outcome: "resolved_unconfirmed",
                created_at: "2026-11-21T19:00:00Z",
                updated_at: "2026-11-21T19:00:05Z",
              },
            ],
          }),
        });
      }

      // Default GET list
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          items: [
            {
              id: "conv_res",
              user_id: "user_demo_01",
              title: "Reset Password",
              status: "active",
              created_at: "2026-11-21T19:00:00Z",
              updated_at: "2026-11-21T19:00:00Z",
              message_count: 2,
              request_count: 1,
            },
          ],
          total: 1,
        }),
      });
    });

    render(<EmployeeView />);

    // Wait for resolution card to appear
    await waitFor(() => {
      expect(
        screen.getByText("L'assistente ritiene che il problema sia stato risolto")
      ).toBeInTheDocument();
    });

    // Verify confirm button with sliding timer bar is present and "Verifica Esito" is removed
    expect(screen.queryByText("Verifica Esito")).not.toBeInTheDocument();
    expect(screen.queryByText("02:00")).not.toBeInTheDocument();
    const confirmBtn = screen.getByRole("button", { name: /Il problema è risolto/i });
    expect(confirmBtn).toBeInTheDocument();

    // Click confirm button
    fireEvent.click(confirmBtn);

    // Resolution success notice should appear
    await waitFor(() => {
      expect(
        screen.getByText(/Richiesta IT contrassegnata come risolta e chiusa con successo/i)
      ).toBeInTheDocument();
    });

    // Input form is no longer rendered and resolved banner is shown
    expect(
      screen.getByText("Problema risolto — Conversazione conclusa")
    ).toBeInTheDocument();
    expect(screen.queryByPlaceholderText(/Descrivi il tuo problema IT/i)).not.toBeInTheDocument();
  });
});

