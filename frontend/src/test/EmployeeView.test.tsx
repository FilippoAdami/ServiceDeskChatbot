import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { EmployeeView } from "../components/EmployeeView";

describe("EmployeeView component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();

    // Mock fetch for conversations and messages
    global.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
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
    expect(screen.getByText(/Assistente AI non attivo in questa versione/i)).toBeInTheDocument();
  });

  it("allows typing and sending a user message", async () => {
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
});
