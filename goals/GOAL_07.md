# GOAL 07 — Hardening, UX e validazione finale della demo

**Stato iniziale:** da implementare  
**Dipendenze:** GOAL 01–06 completati secondo i rispettivi report; verificarne lo stato reale prima di intervenire.  
**Obiettivo:** consegnare una demo locale del Service Desk AI stabile, leggibile, verificabile e riproducibile, senza aggiungere nuove funzionalità di prodotto o cambiare l'architettura concordata.

## 1. Regole di esecuzione

- Leggere `AGENTS.md`, i goal precedenti, il README e il codice esistente; eseguire subito `make check` e registrare il baseline.
- Operare autonomamente fino alla Definition of Done; correggere difetti e aggiungere test. Non dichiarare DONE se una verifica obbligatoria non è stata eseguita o è fallita.
- Conservare React/Vite/TypeScript, FastAPI, SQLAlchemy/SQLite, ChromaDB, FlagEmbedding/BGE-M3 e Gemini. Non introdurre servizi cloud, nuovi framework UI, autenticazione per ruoli o nuove dipendenze importanti senza una motivazione tecnica documentata.
- Mantenere lo switch dimostrativo Dipendente/Tecnico. Non presentarlo come controllo di accesso.
- Non usare `DeterministicFakeEncoder` per dimostrare qualità semantica reale; non sostituire chiamate reali Gemini con mock negli smoke test live. Test offline con fake/mock restano obbligatori per CI e regressioni.
- Non esporre chiavi API, dati sensibili o contenuti di `.env` nei log, screenshot, report o repository. Limitare le chiamate live e non generare spese impreviste.

## 2. Deliverable A — Audit e robustezza funzionale

Eseguire un audit mirato delle funzionalità G01–G06 e correggere problemi riscontrati, con attenzione a:

1. **Conversazioni:** creazione, ripresa dopo refresh e riavvio, ordinamento dei messaggi, più richieste nella stessa conversazione, gestione di messaggi duplicati/invio ripetuto e stato di caricamento.
2. **Agente Gemini:** triage → diagnosi → finalizzazione; configurazione modello e thinking level per fase; contesto persistente; utilizzo motivato delle fonti; distinzione tra fatti della KB e ipotesi; comportamento su input fuori ambito, ambiguo o contenente segreti.
3. **RAG:** indicizzazione reale BGE-M3, recupero multilingue italiano/inglese, query con errori tecnici esatti, filtri `approved`, deduplicazione, reindicizzazione idempotente e ricerca dopo pubblicazione.
4. **Ticketing:** escalation esplicita, idempotenza, ID comunicato solo dopo commit, stato e note modificabili solo tramite azioni autorizzate, correlazione incidenti senza fusione automatica, riapertura conversazione dopo escalation.
5. **Copilota tecnico e KB:** isolamento tra chat dipendente e tecnico, proposte non applicate automaticamente, creazione bozze da entrambi i percorsi di risoluzione, revisione/rifiuto, controllo duplicati, pubblicazione e reindicizzazione con gestione degli errori.
6. **Consistenza:** transazioni DB, migrazioni su database esistente, vincoli FK, timestamp UTC, audit minimale, rollback e recupero da errori parziali.

Non implementare meccanismi complessi di produzione non necessari alla demo; privilegiare correzioni semplici e verificabili.

## 3. Deliverable B — Rifinitura UI/UX

Rifinire l'interfaccia esistente mantenendo il carattere moderno, professionale e moderatamente animato:

- **Leggibilità prima dell'estetica:** contrasto elevato, gerarchia tipografica chiara, spaziature generose, larghezze e lunghezze di riga controllate. Evitare superfici tutte scure e tonalmente indistinguibili.
- **Glass effect selettivo:** usarlo solo dove migliora la gerarchia (ad esempio header/sidebar o modali); evitare blur e trasparenze dietro testo lungo, tabelle e dettagli tecnici.
- **Dashboard tecnico non densa:** panoramica sintetica, ticket in elenco leggibile, dettaglio progressivo, tab distinti, note e copilota consultabili senza sovraccaricare lo schermo. Evitare KPI ornamentali o non supportati dai dati.
- **Chat dipendente:** conversazioni facilmente selezionabili, stato dell'agente e dell'invio comprensibili, riferimenti KB distinguibili, banner ticket persistente, errori e retry espliciti.
- **Interazioni:** feedback su salvataggi, conferme, fallimenti e operazioni lente; stati loading/empty/error; prevenzione di doppi click per azioni non idempotenti; navigazione da tastiera e focus visibile.
- **Responsive:** layout utilizzabile almeno a larghezze desktop e tablet/mobile ragionevoli, senza overflow orizzontale nei percorsi principali.
- **Animazioni:** discrete, non bloccanti, rispettose di `prefers-reduced-motion`; nessun effetto che riduca comprensibilità o prestazioni.

L'agente può riorganizzare componenti frontend per migliorarne manutenibilità, ma non deve rifare inutilmente l'applicazione da zero.

## 4. Deliverable C — Demo riproducibile e osservabilità

- Predisporre **uno scenario dimostrativo riproducibile** che copra: risoluzione bot confermata → proposta KB; problema irrisolto → escalation → ticket tecnico → nota/stato → proposta KB → approvazione → documento recuperabile via RAG.
- Fornire un **seed/reset demo esplicito e sicuro**, documentato, che operi solo sui dati dimostrativi previsti. Prima di cancellare dati, richiedere conferma esplicita o flag CLI dedicato; non eliminare automaticamente dati reali, documenti KB approvati o `.env`. Se esiste già una soluzione, verificarla e migliorarla anziché duplicarla.
- Aggiornare README con prerequisiti, installazione, configurazione `.env` (senza segreti), indicizzazione reale, avvio, test, reset, percorso dimostrativo e troubleshooting.
- Verificare che log ed errori siano utili per la diagnosi ma non contengano password, token, chiavi API o testi integrali sensibili; indicare chiaramente le limitazioni della demo (ruoli simulati, dati mock, assenza di IAM).
- Conservare il funzionamento **local-first**. Docker/deployment online sono **facoltativi**, non bloccanti, e non devono sottrarre tempo ai criteri obbligatori.

## 5. Test obbligatori e quality gate

### 5.1 Regressione automatica

Eseguire realmente `make check` e tutte le verifiche da esso previste: pytest, Vitest, Ruff, mypy, ESLint, TypeScript type-check, Vite build. Ogni correzione funzionale deve avere un test di regressione pertinente.

### 5.2 Test di integrazione e casi limite

Aggiungere o consolidare test deterministici per almeno:

- riavvio backend e recupero di conversazioni, ticket, chat tecnico e proposte;
- escalation ripetuta/concorrenza e assenza di ticket duplicati indesiderati;
- errori Gemini (timeout, rate limit, credenziali mancanti/errate, risposta non valida), con errore comprensibile e dati coerenti;
- indice RAG assente, vuoto o non disponibile; nessuna risposta che inventi procedure aziendali;
- rifiuto di transizioni di stato non valide, note contenenti segreti, doppia approvazione/pubblicazione;
- fallimento di scrittura file o reindicizzazione durante la pubblicazione, con stato recuperabile e senza documento falsamente dichiarato pubblicato;
- controllo che documenti draft/archived non siano recuperati;
- test UI su stati loading/error/empty, conferme, navigazione, switch viste e flussi principali.

### 5.3 Validazione reale dei modelli

- Indicizzare la KB con **BGE-M3 reale**, confermare encoder e dimensioni della collezione e misurare `Recall@5`, `MRR@5`, latenza e numero di query sul dataset italiano esistente. Registrare risultati reali, separati da quelli del fake encoder; non inventare soglie o successi.
- Eseguire almeno uno smoke test live con Gemini che attraversi il percorso dipendente e almeno uno che coinvolga il copilota tecnico, nel rispetto delle quote disponibili. Verificare che modello e thinking level effettivi per triage/diagnosis/finalization corrispondano alla configurazione (medium/high/medium, salvo override documentati).
- Se credenziali, quota o download del modello impediscono un test live, indicare **INCOMPLETO** per la validazione reale e riportare l'ostacolo; non sostituirla silenziosamente con mock.

### 5.4 Verifica manuale browser

Eseguire e documentare un controllo visivo reale (o con strumenti browser disponibili) per le due viste, su almeno desktop e viewport ridotto. Controllare contrasto, densità, overflow, leggibilità, navigazione, stati di errore e percorso completo del ticket. Se il browser non è disponibile, dichiarare la verifica visiva non eseguita e fornire una checklist manuale; non dichiararla superata.

## 6. Criteri di accettazione / Definition of Done

Il goal è **DONE** soltanto se tutti i seguenti punti sono soddisfatti:

- [ ] Baseline G01–G06 verificato e regressioni corrette senza perdita di funzionalità.
- [ ] `make check` completamente verde, con numeri e comandi effettivi riportati.
- [ ] Test dei casi limite sopra elencati implementati ed eseguiti con successo.
- [ ] Percorso completo dipendente → escalation → tecnico → KB verificato con persistenza reale.
- [ ] Percorso bot-resolved → proposta KB → approvazione → RAG verificato.
- [ ] Nessuna modifica automatica di ticket o pubblicazione KB senza conferma del tecnico.
- [ ] Benchmark BGE-M3 **reale** eseguito e metriche documentate separatamente dai test fake.
- [ ] Smoke test **reale** Gemini eseguito; modelli e thinking level per fase verificati.
- [ ] UI leggibile e non sovraffollata; verifica visiva documentata su desktop e viewport ridotto.
- [ ] Stati loading/error/empty e gestione errori utente coperti da test pertinenti.
- [ ] Procedura demo/reset sicura, README aggiornato, avvio riproducibile.
- [ ] Nessun segreto nel repository/log; limiti e rischi residui dichiarati.

Se un criterio è bloccato, consegnare il lavoro svolto con stato **INCOMPLETO**, specificando precisamente evidenza mancante e come riprodurre il blocco. Non indebolire i criteri per ottenere DONE.

## 7. Report finale richiesto

Restituire in modo sintetico:

1. Modifiche principali (file/moduli) e difetti corretti.
2. Comandi realmente eseguiti e risultati dei test, inclusi conteggi.
3. Metriche **BGE-M3 reale** e test **Gemini reale**, distinguendoli dai mock.
4. Evidenze degli scenari end-to-end e della verifica visiva.
5. Istruzioni essenziali per avvio e reset della demo.
6. Limiti residui e stato finale **DONE / INCOMPLETO**.

**Fuori scope:** cloud obbligatorio, IAM/SSO, account separati, microservizi, nuovo provider LLM, analytics avanzati non necessari, nuove feature non richieste.
