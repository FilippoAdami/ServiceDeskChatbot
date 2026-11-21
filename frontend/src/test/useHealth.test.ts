import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useHealth } from "../hooks/useHealth";

describe("useHealth hook", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("fetches and returns successful health response", async () => {
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

    const { result } = renderHook(() => useHealth("/api/health"));

    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.status).toBe("ok");
    expect(result.current.data?.database).toBe("connected");
    expect(result.current.error).toBeNull();
    expect(result.current.latencyMs).toBeTypeOf("number");
  });

  it("handles non-200 error response from server", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      statusText: "Service Unavailable",
      json: async () => ({
        status: "error",
        database: "disconnected",
        detail: "Database connection unreachable",
      }),
    });

    const { result } = renderHook(() => useHealth("/api/health"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe("Database connection unreachable");
  });

  it("handles network failure gracefully", async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error("Connection refused"));

    const { result } = renderHook(() => useHealth("/api/health"));

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe("Connection refused");
  });
});
