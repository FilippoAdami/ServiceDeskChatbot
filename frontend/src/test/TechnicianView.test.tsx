import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TechnicianView } from "../components/TechnicianView";

describe("TechnicianView component", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders empty state when no support requests exist", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
      }),
    });

    render(<TechnicianView />);

    await waitFor(() => {
      expect(screen.getByText("Nessuna richiesta registrata")).toBeInTheDocument();
    });

    expect(screen.getByText("Elenco Problematiche IT Registrate")).toBeInTheDocument();
  });

  it("renders table of support requests when items are present", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [
          {
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
          },
        ],
        total: 1,
        limit: 50,
        offset: 0,
      }),
    });

    render(<TechnicianView />);

    await waitFor(() => {
      expect(screen.getByText("Blocco account Active Directory")).toBeInTheDocument();
    });

    expect(screen.getByText("req_101")).toBeInTheDocument();
    expect(screen.getByText("open")).toBeInTheDocument();
    expect(screen.getByText("account")).toBeInTheDocument();
  });

  it("handles filter changes and triggers fetch", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        items: [],
        total: 0,
        limit: 50,
        offset: 0,
      }),
    });
    global.fetch = fetchMock;

    render(<TechnicianView />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const filterSelect = screen.getByLabelText(/Stato:/i);
    fireEvent.change(filterSelect, { target: { value: "closed" } });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("status=closed"));
    });
  });
});
