import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { ConnectionBadge } from "../components/ConnectionBadge";
import type { UseHealthResult } from "../hooks/useHealth";

describe("ConnectionBadge component", () => {
  it("renders loading state when initial check is pending", () => {
    const loadingState: UseHealthResult = {
      data: null,
      isLoading: true,
      error: null,
      latencyMs: null,
      lastChecked: null,
      refetch: vi.fn(),
    };

    render(<ConnectionBadge healthState={loadingState} />);
    expect(screen.getByTestId("connection-loading")).toBeInTheDocument();
    expect(screen.getByText(/Verifica connessione API/i)).toBeInTheDocument();
  });

  it("renders online state when backend health check succeeds", () => {
    const onlineState: UseHealthResult = {
      data: {
        status: "ok",
        database: "connected",
        timestamp: "2026-11-21T19:00:00Z",
        version: "0.1.0",
        environment: "development",
        detail: null,
      },
      isLoading: false,
      error: null,
      latencyMs: 14,
      lastChecked: new Date(),
      refetch: vi.fn(),
    };

    render(<ConnectionBadge healthState={onlineState} />);
    expect(screen.getByTestId("connection-online")).toBeInTheDocument();
    expect(screen.getByText("API Online")).toBeInTheDocument();
    expect(screen.getByText("v0.1.0")).toBeInTheDocument();
    expect(screen.getByText(/DB Attivo/i)).toBeInTheDocument();
    expect(screen.getByText("14ms")).toBeInTheDocument();
  });

  it("renders error state when backend health check fails or returns error", () => {
    const refetchMock = vi.fn();
    const errorState: UseHealthResult = {
      data: null,
      isLoading: false,
      error: "Impossibile contattare il server API",
      latencyMs: 25,
      lastChecked: new Date(),
      refetch: refetchMock,
    };

    render(<ConnectionBadge healthState={errorState} />);
    expect(screen.getByTestId("connection-error")).toBeInTheDocument();
    expect(screen.getByText(/Backend Disconnesso/i)).toBeInTheDocument();

    const retryButton = screen.getByRole("button", { name: /Riprova connessione/i });
    expect(retryButton).toBeInTheDocument();
    fireEvent.click(retryButton);
    expect(refetchMock).toHaveBeenCalledTimes(1);
  });
});
