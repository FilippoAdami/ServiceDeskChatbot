import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TechnicianView } from "../components/TechnicianView";

const mockTicket = {
  id: "tkt_001",
  support_request_id: "req_001",
  conversation_id: "conv_001",
  title: "Titolo Ticket VPN",
  summary: "Riepilogo disservizio autenticazione VPN Cisco",
  status: "open",
  priority: "high",
  summary_quality: "llm",
  incident_id: null,
  created_at: "2026-11-21T19:00:00Z",
  updated_at: "2026-11-21T19:00:00Z",
};

const mockTicketDetail = {
  ...mockTicket,
  symptoms: "L'utente non riesce a connettersi al client VPN Cisco",
  attempted_steps: "Riavvio client, verifica credenziali",
  diagnostic_findings: "Certificato scaduto su profilo locale",
  source_refs: ["KB-NET-001"],
  activities: [
    {
      id: "act_001",
      ticket_id: "tkt_001",
      activity_type: "created",
      author: "system_escalation",
      author_role: "system",
      content: "Ticket creato a seguito di escalation",
      old_status: null,
      new_status: "open",
      created_at: "2026-11-21T19:00:00Z",
    },
  ],
};

const mockIncident = {
  id: "INC-2026-001",
  service: "Posta Elettronica Exchange",
  title: "Degrado prestazioni server Exchange",
  summary: "Rallentamento nella ricezione email",
  symptoms: "Connessioni lente IMAP/SMTP",
  status: "investigating",
  ticket_count: 2,
  created_at: "2026-11-21T18:00:00Z",
  updated_at: "2026-11-21T18:30:00Z",
};

const mockSupportRequest = {
  id: "req_101",
  conversation_id: "conv_1",
  title: "Blocco account Active Directory",
  description: "Utente inserito password errata 3 volte",
  initial_category: "account",
  final_category: null,
  status: "open",
  outcome: null,
  created_at: "2026-11-21T19:00:00Z",
  updated_at: "2026-11-21T19:00:00Z",
};

function setupFetchMock(customResponses?: Record<string, unknown>) {
  return vi.fn().mockImplementation((url: string, options?: RequestInit) => {
    const method = options?.method || "GET";

    if (customResponses && url in customResponses) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => customResponses[url],
      });
    }

    if (url.includes("/api/tickets/tkt_001/status") && method === "POST") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ ...mockTicketDetail, status: "in_progress" }),
      });
    }

    if (url.includes("/api/tickets/tkt_001/notes") && method === "POST") {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          id: "act_002",
          ticket_id: "tkt_001",
          activity_type: "note",
          author: "technician_demo",
          author_role: "technician",
          content: "Nota tecnica aggiunta",
          old_status: null,
          new_status: null,
          created_at: "2026-11-21T19:10:00Z",
        }),
      });
    }

    if (url.includes("/api/tickets/tkt_001/chat")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => [],
      });
    }

    if (url.includes("/api/kb-proposals")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          items: [],
          total: 0,
          limit: 50,
          offset: 0,
        }),
      });
    }

    if (url.includes("/api/tickets/tkt_001")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => mockTicketDetail,
      });
    }

    if (url.includes("/api/tickets")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          items: [mockTicket],
          total: 1,
          limit: 50,
          offset: 0,
        }),
      });
    }

    if (url.includes("/api/incidents")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          items: [mockIncident],
          total: 1,
          limit: 50,
          offset: 0,
        }),
      });
    }

    if (url.includes("/api/requests")) {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          items: [mockSupportRequest],
          total: 1,
          limit: 50,
          offset: 0,
        }),
      });
    }

    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0 }),
    });
  });
}

describe("TechnicianView component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders empty state when no tickets exist", async () => {
    global.fetch = vi.fn().mockImplementation((_url: string) => {
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({ items: [], total: 0, limit: 50, offset: 0 }),
      });
    });

    render(<TechnicianView />);

    await waitFor(() => {
      expect(screen.getByText("Nessun ticket presente")).toBeInTheDocument();
    });

    expect(screen.getByText("Ticket Service Desk")).toBeInTheDocument();
    expect(screen.getByText("Nessun ticket selezionato")).toBeInTheDocument();
  });

  it("renders ticket list, diagnostic findings, and allows status transition", async () => {
    const fetchMock = setupFetchMock();
    global.fetch = fetchMock;

    render(<TechnicianView />);

    // Check ticket list rendered
    await waitFor(() => {
      expect(screen.getAllByText("Titolo Ticket VPN").length).toBeGreaterThan(0);
    });

    // Check detail pane rendered with diagnostic information
    expect(screen.getByText("Sintomi Rilevati")).toBeInTheDocument();
    expect(screen.getByText("L'utente non riesce a connettersi al client VPN Cisco")).toBeInTheDocument();
    expect(screen.getByText("Certificato scaduto su profilo locale")).toBeInTheDocument();
    expect(screen.getByText("KB-NET-001")).toBeInTheDocument();

    // Verify status transition action: open -> in_progress ("Passa a In lavorazione")
    const inProgressBtn = screen.getByRole("button", { name: /Passa a In lavorazione/i });
    expect(inProgressBtn).toBeInTheDocument();
    fireEvent.click(inProgressBtn);

    // Verify confirmation prompt appeared
    const confirmBtn = screen.getByRole("button", { name: /Conferma Cambio Stato/i });
    expect(confirmBtn).toBeInTheDocument();

    // Confirm transition
    fireEvent.click(confirmBtn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/tickets/tkt_001/status"),
        expect.objectContaining({ method: "POST" })
      );
    });
  });

  it("allows adding technical notes to a ticket", async () => {
    const fetchMock = setupFetchMock();
    global.fetch = fetchMock;

    render(<TechnicianView />);

    await waitFor(() => {
      expect(screen.getAllByText("Titolo Ticket VPN").length).toBeGreaterThan(0);
    });

    const noteInput = screen.getByPlaceholderText(/Aggiungi una nota tecnica/i);
    fireEvent.change(noteInput, { target: { value: "Verificato server RADIUS, tutto operativo." } });

    const submitBtn = screen.getByRole("button", { name: /Aggiungi Nota/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/tickets/tkt_001/notes"),
        expect.objectContaining({
          method: "POST",
          body: expect.stringContaining("Verificato server RADIUS"),
        })
      );
    });
  });

  it("switches to 'Incidenti Noti' tab and displays company incidents", async () => {
    global.fetch = setupFetchMock();

    render(<TechnicianView />);

    const incidentsTab = screen.getByRole("button", { name: /Incidenti Noti/i });
    fireEvent.click(incidentsTab);

    await waitFor(() => {
      expect(screen.getByText("Incidenti e Disservizi Noti Aziendali")).toBeInTheDocument();
      expect(screen.getByText("Degrado prestazioni server Exchange")).toBeInTheDocument();
      expect(screen.getByText("Posta Elettronica Exchange")).toBeInTheDocument();
    });
  });

  it("switches to 'Tutte le Richieste' tab, renders support requests and handles filtering", async () => {
    const fetchMock = setupFetchMock();
    global.fetch = fetchMock;

    render(<TechnicianView />);

    const requestsTab = screen.getByRole("button", { name: /Tutte le Richieste/i });
    fireEvent.click(requestsTab);

    await waitFor(() => {
      expect(screen.getByText("Elenco Problematiche IT Registrate")).toBeInTheDocument();
      expect(screen.getByText("Blocco account Active Directory")).toBeInTheDocument();
    });

    // Test filter change
    const filterSelect = screen.getByLabelText(/Stato:/i);
    fireEvent.change(filterSelect, { target: { value: "closed" } });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("status=closed"));
    });
  });
});
