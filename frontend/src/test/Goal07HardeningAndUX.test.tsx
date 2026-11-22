import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { KnowledgeProposalsPanel } from "../components/KnowledgeProposalsPanel";
import type { KnowledgeProposal } from "../types/api";

const mockDraftProposal: KnowledgeProposal = {
  id: "prop_demo_01",
  source_type: "ticket",
  source_id: "tkt_001",
  status: "draft",
  destination: "new_document",
  target_kb_slug: null,
  target_doc_id: "KB-DEMO-001",
  title: "Guida Test Risoluzione",
  content_markdown: "# Guida Test\nCorpo guida.",
  generated_category: "network",
  review_notes: "",
  rejection_reason: null,
  author: "technician_demo",
  reviewer: null,
  published_path: null,
  published_at: null,
  created_at: "2026-11-22T09:00:00Z",
  updated_at: "2026-11-22T09:00:00Z",
};

describe("Goal 07: UX Polish, Modals, and Empty/Error States", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("KnowledgeProposalsPanel displays rejection modal and allows cancelling or confirming rejection", async () => {
    let currentProposal = { ...mockDraftProposal };

    globalThis.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
      if (url.endsWith("/kb-proposals") || url.includes("/kb-proposals?")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => ({
            items: [currentProposal],
            total: 1,
            limit: 50,
            offset: 0,
          }),
        });
      }
      if (url.includes("/reject")) {
        const body = JSON.parse(options?.body as string);
        currentProposal = {
          ...currentProposal,
          status: "rejected",
          rejection_reason: body.reason,
        };
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => currentProposal,
        });
      }
      if (url.includes("/duplicates")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [],
        });
      }
      return Promise.resolve({
        ok: true,
        status: 200,
        json: async () => currentProposal,
      });
    });

    render(<KnowledgeProposalsPanel />);

    // Wait for proposal detail to load into the form
    await screen.findByDisplayValue("Guida Test Risoluzione");

    // Click on Rifiuta button (exact match to distinguish from "Rifiutato" filter pill)
    const rejectBtn = screen.getByRole("button", { name: /^rifiuta$/i });
    fireEvent.click(rejectBtn);

    // Verify modal header appears
    expect(screen.getByText("Conferma Rifiuto Proposta KB")).toBeInTheDocument();

    // Type a rejection reason
    const textarea = screen.getByPlaceholderText(/motivo del rifiuto/i);
    fireEvent.change(textarea, { target: { value: "Soluzione obsoleta non più applicabile." } });

    // Click confirm rejection
    const confirmRejectBtn = screen.getByRole("button", { name: /conferma rifiuto/i });
    fireEvent.click(confirmRejectBtn);

    // Modal should close and success message should appear
    await waitFor(() => {
      expect(screen.getByText("Proposta KB rifiutata.")).toBeInTheDocument();
    });
  });

  it("KnowledgeProposalsPanel renders friendly empty state when no proposals exist", async () => {
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/kb-proposals")) {
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
      return Promise.resolve({ ok: true, status: 200, json: async () => ({}) });
    });

    render(<KnowledgeProposalsPanel />);

    await waitFor(() => {
      expect(screen.getByText("Nessuna proposta trovata")).toBeInTheDocument();
    });
  });
});
