import { render, screen, waitFor, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { TechnicianChatPanel } from "../components/TechnicianChatPanel";
import { KnowledgeProposalsPanel } from "../components/KnowledgeProposalsPanel";
import type { TicketDetail, KnowledgeProposal, DuplicateCandidate } from "../types/api";

const mockTicket: TicketDetail = {
  id: "tkt_vpn_01",
  support_request_id: "req_vpn_01",
  conversation_id: "conv_vpn_01",
  incident_id: null,
  status: "in_progress",
  priority: "high",
  title: "VPN Cisco fallisce autenticazione",
  summary: "Errore certificato utente",
  summary_quality: "llm",
  created_at: "2026-11-22T08:00:00Z",
  updated_at: "2026-11-22T08:00:00Z",
  symptoms: "Client VPN riporta Certificato Scaduto",
  attempted_steps: "Reinstallazione client",
  diagnostic_findings: "Rinnovare certificato su portale",
  source_refs: ["KB-NET-001"],
  activities: [],
};

const mockDraftProposal: KnowledgeProposal = {
  id: "prop_kb_01",
  source_type: "ticket",
  source_id: "tkt_vpn_01",
  status: "draft",
  destination: "new_document",
  target_kb_slug: null,
  target_doc_id: "KB-NET-002",
  title: "Risoluzione Errore Certificato VPN Cisco",
  content_markdown: "---\nid: KB-NET-002\ntitle: Risoluzione Errore Certificato VPN Cisco\ncategory: Rete\nstatus: approved\n---\n# Procedura Rinnovo\nAccedere al portale PKI.",
  generated_category: "Rete",
  review_notes: "",
  rejection_reason: null,
  author: "technician_demo",
  reviewer: null,
  published_path: null,
  published_at: null,
  created_at: "2026-11-22T08:30:00Z",
  updated_at: "2026-11-22T08:30:00Z",
};

const mockDuplicate: DuplicateCandidate = {
  slug: "vpn-troubleshooting.md",
  doc_id: "KB-NET-001",
  title: "Guida VPN e Connessioni Remote",
  category: "Rete",
  similarity: 0.88,
  preview: "Controllare la scadenza del certificato e il client Cisco AnyConnect.",
};

describe("Goal 06: Technician AI Assistant & Knowledge Improvement", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("TechnicianChatPanel renders chat history and displays operational proposals with confirmation action", async () => {
    const onApply = vi.fn().mockResolvedValue(undefined);

    const initialMessages = [
      {
        id: "msg_tech_1",
        ticket_id: "tkt_vpn_01",
        author_type: "technician",
        author_name: "technician_demo",
        content: "Cosa consiglia la procedura per certificato scaduto?",
        created_at: "2026-11-22T08:10:00Z",
      },
      {
        id: "msg_ai_1",
        ticket_id: "tkt_vpn_01",
        author_type: "assistant",
        author_name: "copilot_technician",
        content: "In base all'articolo KB-NET-001, il certificato va revocato e rigenerato tramite portale PKI.",
        operational_proposals: {
          proposed_status: "resolved",
          proposed_note: "Certificato VPN rigenerato tramite portale self-service PKI.",
          proposed_cause: "Certificato client X.509 scaduto",
          proposed_solution: "Rigenerazione e import nel keychain",
        },
        created_at: "2026-11-22T08:11:00Z",
      },
    ];

    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes("/chat")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => initialMessages,
        });
      }
      return Promise.reject(new Error("URL non gestita"));
    });

    render(<TechnicianChatPanel ticket={mockTicket} onApplyProposal={onApply} />);

    // Check header
    expect(screen.getByText("Copilota AI Tecnico")).toBeInTheDocument();

    // Wait for message rendering
    await waitFor(() => {
      expect(
        screen.getByText(/In base all'articolo KB-NET-001, il certificato va revocato/)
      ).toBeInTheDocument();
    });

    // Check operational proposals card
    expect(screen.getByText("Proposta Operativa Suggerita")).toBeInTheDocument();
    expect(screen.getByText("resolved")).toBeInTheDocument();
    expect(screen.getByText(/Certificato VPN rigenerato tramite portale/)).toBeInTheDocument();

    // Check apply button
    const applyBtn = screen.getByRole("button", { name: /Applica Nota e Stato al Ticket/i });
    expect(applyBtn).toBeInTheDocument();

    // Click apply button
    fireEvent.click(applyBtn);

    await waitFor(() => {
      expect(onApply).toHaveBeenCalledWith(
        "resolved",
        "Certificato VPN rigenerato tramite portale self-service PKI."
      );
    });
  });

  it("KnowledgeProposalsPanel loads draft proposals, allows Markdown editing, duplicate check, and approval", async () => {
    let currentProposal = { ...mockDraftProposal };

    globalThis.fetch = vi.fn().mockImplementation((url: string, opts?: RequestInit) => {
      const method = opts?.method || "GET";

      if (url.includes("/duplicates")) {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => [mockDuplicate],
        });
      }

      if (url.includes("/publish") && method === "POST") {
        currentProposal = {
          ...currentProposal,
          status: "approved",
          published_path: "knowledge_base/rete/risoluzione-errore-certificato-vpn-cisco.md",
        };
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => currentProposal,
        });
      }

      if (url.includes("/kb-proposals/prop_kb_01") && method === "PUT") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => currentProposal,
        });
      }

      if (url.includes("/kb-proposals/prop_kb_01") && method === "GET") {
        return Promise.resolve({
          ok: true,
          status: 200,
          json: async () => currentProposal,
        });
      }

      if (url.includes("/kb-proposals")) {
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

      return Promise.reject(new Error("URL non gestita: " + url));
    });

    render(<KnowledgeProposalsPanel />);

    // Wait for proposal item in list
    await waitFor(() => {
      expect(screen.getByText("Risoluzione Errore Certificato VPN Cisco")).toBeInTheDocument();
    });

    // Check detail editor fields
    expect(screen.getByDisplayValue("Risoluzione Errore Certificato VPN Cisco")).toBeInTheDocument();
    expect(screen.getByDisplayValue(/# Procedura Rinnovo/)).toBeInTheDocument();

    // Check duplicates
    const dupBtn = screen.getByRole("button", { name: /Cerca Articoli Simili/i });
    fireEvent.click(dupBtn);

    await waitFor(() => {
      expect(screen.getByText(/88% sim/i)).toBeInTheDocument();
      expect(screen.getByText("Guida VPN e Connessioni Remote")).toBeInTheDocument();
    });

    // Approve and publish
    const publishBtn = screen.getByRole("button", { name: /Approva e Pubblica Articolo/i });
    fireEvent.click(publishBtn);

    await waitFor(() => {
      expect(screen.getByText(/Articolo approvato e pubblicato con successo/i)).toBeInTheDocument();
    });
  });
});
