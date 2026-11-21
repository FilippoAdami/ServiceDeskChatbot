import React from "react";
import { MessageSquare, ShieldCheck, Cpu, ArrowRight } from "lucide-react";

export const EmployeePlaceholder: React.FC = () => {
  return (
    <section
      id="panel-employee"
      role="tabpanel"
      aria-labelledby="tab-employee"
      className="space-y-6"
    >
      {/* Welcome Card */}
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm md:p-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-1 text-xs font-semibold text-primary">
              <MessageSquare className="h-3.5 w-3.5" />
              <span>Vista Dipendente — Assistenza IT</span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Canale di Supporto Diretto per Dipendenti
            </h2>
            <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
              Questa vista consentirà ai dipendenti dell&apos;azienda di descrivere problemi
              tecnici ricorrenti (reset password, anomalie casella di posta, configurazione VPN e
              applicativi aziendali) per ricevere diagnosi assistita autonoma o escalation diretta.
            </p>
          </div>

          <div className="flex shrink-0 flex-col gap-2 rounded-xl border border-border/80 bg-background/60 p-4 text-xs">
            <span className="font-semibold text-foreground">Stato Milestone G01:</span>
            <div className="flex items-center gap-2 text-emerald-400">
              <ShieldCheck className="h-4 w-4" />
              <span>Shell frontend e routing pronti</span>
            </div>
            <div className="flex items-center gap-2 text-emerald-400">
              <ShieldCheck className="h-4 w-4" />
              <span>API FastAPI e SQLite operativi</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Cpu className="h-4 w-4" />
              <span>Orchestrazione LLM prevista per G04</span>
            </div>
          </div>
        </div>
      </div>

      {/* Workflow Preview Cards (Explicitly marked as planned, no fake chatbot) */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-xl border border-border bg-card p-5 space-y-2">
          <div className="flex items-center gap-2 text-primary font-semibold text-sm">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/20 text-xs text-primary">
              1
            </span>
            <span>Triage Iniziale</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Raccolta interattiva dei sintomi, determinazione preliminare del contesto applicativo
            e della gravità, senza bloccare la conversazione.
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5 space-y-2">
          <div className="flex items-center gap-2 text-primary font-semibold text-sm">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/20 text-xs text-primary">
              2
            </span>
            <span>Diagnosi Assistita</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Consultazione automatica della Knowledge Base aziendale (RAG locale con BGE-M3) e
            verifica di eventuali incidenti IT già aperti.
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card p-5 space-y-2">
          <div className="flex items-center gap-2 text-primary font-semibold text-sm">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/20 text-xs text-primary">
              3
            </span>
            <span>Risoluzione / Escalation</span>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Verifica esplicita dell&apos;esito con il dipendente oppure generazione controllata di un
            ticket interno indirizzato al team di supporto.
          </p>
        </div>
      </div>

      {/* Chat Area Placeholder (clean, non-fake) */}
      <div className="rounded-2xl border border-dashed border-border bg-card/40 p-10 text-center">
        <div className="mx-auto max-w-md space-y-3">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
            <MessageSquare className="h-6 w-6" />
          </div>
          <h3 className="text-base font-semibold text-foreground">
            Area Conversazione (Milestone G02 / G04)
          </h3>
          <p className="text-xs text-muted-foreground leading-relaxed">
            In conformità con i requisiti di G01, l&apos;interfaccia non include finti bot o
            simulazioni hardcoded. La chat interattiva verrà integrata con la persistenza della
            conversazione in G02 e l&apos;agente Gemini in G04.
          </p>
          <div className="pt-2">
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-primary">
              <span>Prossima tappa: Persistenza e contratti G02</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </span>
          </div>
        </div>
      </div>
    </section>
  );
};
