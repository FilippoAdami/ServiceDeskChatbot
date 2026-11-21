import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../App";

describe("App shell and view switching", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    // Default fetch mock returning 200 OK
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        status: "ok",
        database: "connected",
        timestamp: "2026-11-21T19:00:00Z",
        version: "0.1.0",
        environment: "development",
        detail: null,
      }),
    });
  });

  it("renders employee view by default and switches to technician view on click", async () => {
    render(<App />);

    // Check title and brand
    expect(screen.getByText("Service Desk AI")).toBeInTheDocument();

    // Default view is employee
    expect(
      screen.getByText("Vista Dipendente — Assistenza IT")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Canale di Supporto Diretto per Dipendenti")
    ).toBeInTheDocument();

    // Verify online badge is displayed after health check completes
    await waitFor(() => {
      expect(screen.getByTestId("connection-online")).toBeInTheDocument();
    });

    // Switch to Technician view
    const techTab = screen.getByRole("tab", { name: /Vista Tecnico/i });
    fireEvent.click(techTab);

    // Verify view changed without page reload
    await waitFor(() => {
      expect(
        screen.getByText("Vista Tecnico IT — Console Operativa")
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText("Console di Gestione e Supervisione IT")
    ).toBeInTheDocument();
    expect(
      screen.queryByText("Canale di Supporto Diretto per Dipendenti")
    ).not.toBeInTheDocument();

    // Switch back to Employee view
    const empTab = screen.getByRole("tab", { name: /Vista Dipendente/i });
    fireEvent.click(empTab);

    await waitFor(() => {
      expect(
        screen.getByText("Vista Dipendente — Assistenza IT")
      ).toBeInTheDocument();
    });
  });

  it("reflects backend error in the shell when health check fails", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("Network connection refused"));

    render(<App />);

    await waitFor(() => {
      expect(screen.getByTestId("connection-error")).toBeInTheDocument();
    });
    expect(screen.getByText(/Backend Disconnesso/i)).toBeInTheDocument();
  });
});
