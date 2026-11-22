import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import App from "../App";

describe("App shell and view switching", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    global.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/api/health")) {
        return Promise.resolve({
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
      }
      if (url.includes("/api/conversations")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            items: [
              {
                id: "conv_test_1",
                user_id: "user_demo_01",
                title: "Problema accesso email",
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
      }
      if (url.includes("/api/requests")) {
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
      if (url.includes("/api/tickets")) {
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
      if (url.includes("/api/incidents")) {
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
      if (url.includes("/api/audit/events")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            items: [],
            total: 0,
            limit: 100,
            offset: 0,
          }),
        });
      }
      if (url.includes("/api/audit/conversations")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            items: [],
            total: 0,
          }),
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => ({
          id: "conv_test_1",
          user_id: "user_demo_01",
          title: "Problema accesso email",
          status: "active",
          created_at: "2026-11-21T19:00:00Z",
          updated_at: "2026-11-21T19:00:00Z",
          messages: [],
          requests: [],
        }),
      });
    });
  });

  it("renders employee view by default and switches to technician view on click", async () => {
    render(<App />);

    // Check title and brand
    expect(screen.getByText("Service Desk AI")).toBeInTheDocument();

    // Default view shows EmployeeView components
    expect(screen.getByText("Conversazioni")).toBeInTheDocument();
    expect(screen.getByText("Nuova Chat")).toBeInTheDocument();

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
        screen.getByText("Console Tecnico IT — Richieste Supporto Reali")
      ).toBeInTheDocument();
    });
    expect(
      screen.getByText("Ticket Service Desk")
    ).toBeInTheDocument();

    // Switch to Debug & Audit view
    const debugTab = screen.getByRole("tab", { name: /Debug & Audit/i });
    fireEvent.click(debugTab);

    await waitFor(() => {
      expect(
        screen.getByText("Console Live Debug & Audit Eventi")
      ).toBeInTheDocument();
    });

    // Switch back to Employee view
    const empTab = screen.getByRole("tab", { name: /Vista Dipendente/i });
    fireEvent.click(empTab);

    await waitFor(() => {
      expect(screen.getByText("Conversazioni")).toBeInTheDocument();
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
