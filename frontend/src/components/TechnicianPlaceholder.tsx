import React from "react";
import { Wrench, Ticket, AlertTriangle, BookOpen, Layers } from "lucide-react";

export const TechnicianPlaceholder: React.FC = () => {
  return (
    <section
      id="panel-technician"
      role="tabpanel"
      aria-labelledby="tab-technician"
      className="space-y-6"
    >
      {/* Overview Card */}
      <div className="rounded-2xl border border-border bg-card p-6 shadow-sm md:p-8">
        <div className="flex flex-col gap-6 md:flex-row md:items-start md:justify-between">
          <div className="max-w-2xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-lg bg-accent px-3 py-1 text-xs font-semibold text-accent-foreground">
              <Wrench className="h-3.5 w-3.5" />
              <span>Vista Tecnico IT — Console Operativa</span>
            </div>
            <h2 className="text-2xl font-bold tracking-tight text-foreground sm:text-3xl">
              Console di Gestione e Supervisione IT
            </h2>
            <p className="text-sm leading-relaxed text-muted-foreground sm:text-base">
              Questa console dedicata ai tecnici di supporto permetterà di monitorare i ticket
              aperti dal bot in caso di escalation, verificare incidenti infrastrutturali correlati
              e validare le nuove proposte di documentazione per la Knowledge Base.
            </p>
          </div>

          <div className="flex shrink-0 flex-col gap-2 rounded-xl border border-border/80 bg-background/60 p-4 text-xs">
            <span className="font-semibold text-foreground">Architettura G01:</span>
            <div className="flex items-center gap-2 text-primary">
              <Layers className="h-4 w-4" />
              <span>Contratti API tipizzati e validati</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <Ticket className="h-4 w-4" />
              <span>Adapter Ticket & Incidenti previsti per G05</span>
            </div>
            <div className="flex items-center gap-2 text-muted-foreground">
              <BookOpen className="h-4 w-4" />
              <span>Revisione Knowledge Base prevista per G05</span>
            </div>
          </div>
        </div>
      </div>

      {/* Planned Operational Modules (no dense fake data) */}
      <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
        <div className="rounded-xl border border-border bg-card/70 p-6 space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary text-primary">
              <Ticket className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Coda Ticket Escalati</h3>
              <span className="text-[11px] text-muted-foreground">Milestone G05</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Visualizzazione dei ticket aperti per problemi non risolvibili autonomamente o su
            richiesta esplicita del dipendente, con storico diagnostico allegato.
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card/70 p-6 space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary text-amber-400">
              <AlertTriangle className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Incident Awareness</h3>
              <span className="text-[11px] text-muted-foreground">Milestone G05</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Rilevamento e correlazione semantica di anomalie condivise (es. disservizio server posta
            o switch di rete) per evitare aperture duplicate di ticket.
          </p>
        </div>

        <div className="rounded-xl border border-border bg-card/70 p-6 space-y-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-secondary text-emerald-400">
              <BookOpen className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-foreground">Bozze Knowledge Base</h3>
              <span className="text-[11px] text-muted-foreground">Milestone G05</span>
            </div>
          </div>
          <p className="text-xs text-muted-foreground leading-relaxed">
            Workflow di revisione ed approvazione umana delle procedure estratte dalle risoluzioni
            confermate, prima della pubblicazione nell&apos;indice vettoriale.
          </p>
        </div>
      </div>

      {/* Info notice */}
      <div className="rounded-xl border border-border/80 bg-background/50 p-6 text-center text-xs text-muted-foreground">
        <p>
          Come previsto dai vincoli di <strong>GOAL 01</strong>, nessuna dashboard simulata densa
          o finto dataset sono stati introdotti. I collegamenti reali con il DB SQLite e il
          backend FastAPI sono già predisposti.
        </p>
      </div>
    </section>
  );
};
