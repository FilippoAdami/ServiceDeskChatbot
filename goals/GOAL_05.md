# GOAL 05 — Ticketing, escalation e operatività del tecnico

**Stato:** da implementare  
**Prerequisiti:** GOAL 01–04; verificare nel repository codice, migrazioni, test e stato effettivo di Gemini/BGE-M3 prima di intervenire.  
**Obiettivo:** chiudere il ciclo di escalation dal chatbot del dipendente alla gestione umana: un problema non risolto genera un **ticket mock persistente**, visibile nella vista Tecnico con **riepilogo diagnostico attendibile**; il tecnico può consultarlo, aggiornarne stato e note e collegarlo a incidenti noti. Le modifiche sono tracciate e non avvengono sulla base di sole affermazioni non verificate del modello.

## 1. Contratto e confini

- Conservare la distinzione **Conversation → SupportRequest → Ticket**: ogni problema IT ha una richiesta, anche quando risolto dal bot; il ticket nasce **solo in caso di escalation**. La conversazione resta aperta e riprendibile dopo la creazione del ticket.
- Riutilizzare l'orchestrazione Gemini e la finalizzazione di G04 per produrre un **riepilogo strutturato**, validato dal backend, basato su messaggi ed eventi realmente persistiti. Se Gemini non è disponibile, l'escalation deve comunque essere possibile con un riepilogo minimale deterministico, **chiaramente marcato come tale**; mai inventare diagnosi o azioni.
- Ticketing esterno **simulato tramite adapter locale**; nessuna integrazione reale con sistemi aziendali. Operazioni di scrittura e transizioni di stato sono autorizzate **solo dal backend**, non da testo libero dell'LLM.
- La vista Tecnico deve essere **operativa e leggibile**, non una dashboard analitica completa: lista essenziale, dettaglio, modifica stato, note, storico e indicazione delle correlazioni. Aggiornamento tramite refresh o polling semplice, senza obbligo di WebSocket.
- I ruoli Dipendente/Tecnico sono **viste demo selezionabili**, non un sistema IAM. Non dichiarare isolamento/autorizzazione multiutente reale. API operative solo per uso locale; documentare il rischio e non esporle pubblicamente senza protezione.
- **Rinviare a G06:** chat AI dedicata al tecnico, estrazione conversazionale degli interventi, generazione/revisione/approvazione/pubblicazione di bozze KB, reindicizzazione a seguito di approvazione, dashboard KPI avanzata e rifinitura visiva estesa. G05 deve predisporre dati e interfacce riutilizzabili per G06, senza implementarlo in anticipo.

## 2. Deliverable

### A. Persistenza, migrazioni e invarianti

1. Introdurre `Ticket`, `TicketNote`/`TicketActivity` e `Incident` (ed eventuale relazione di correlazione) con SQLAlchemy e **migrazione Alembic compatibile** con i dati G01–G04. Adattare nomi/campi alla struttura reale del repository, senza duplicare entità esistenti.
2. `Ticket`: ID stabile, `support_request_id`, stato, priorità se giustificata, `created_at`/`updated_at` UTC, `summary`, `symptoms`, `attempted_steps`, `diagnostic_findings`, `source_refs`, eventuale `incident_id`; conservare provenienza/qualità del riepilogo (`llm`/`fallback`) e riferimenti alla conversazione. Non inventare campi clinici o dati personali superflui.
3. `TicketNote`/attività: autore demo (`technician`/`system`), testo sanificato, timestamp e tipo evento. Conservare cronologia delle transizioni; una nota non equivale automaticamente a un cambiamento di stato.
4. `Incident`: identificativo, servizio, sintomi, stato, `created_at`/`updated_at`, sintesi pubblica sanificata e relazione a più richieste/ticket. Correlazioni **suggerite**, confermate dal tecnico; non fondere né eliminare richieste individuali.
5. Definire una **macchina a stati esplicita** per il ticket (es. `open → in_progress → resolved → closed`, con riapertura controllata), validata lato server. Distinguere chiaramente stato del ticket ed esito della `SupportRequest`. Un ticket `resolved` non equivale automaticamente a `resolved_confirmed` dall'utente.
6. Vincoli referenziali, indici e transazioni atomiche; comportamento esplicito per tentativi ripetuti di escalation (idempotenza) e richieste concorrenti. Non introdurre l'invariante universale «un solo ticket per richiesta» senza valutazione: per la demo prevenire duplicati involontari con una chiave/operazione idempotente, mantenendo estensibilità per casi distinti.

### B. Escalation dal chatbot

1. Riconoscere sia l'**esplicita richiesta di un tecnico** sia l'escalation proposta dall'agente dopo troubleshooting insufficiente. Nessuna soglia rigida di turni come unica condizione; il backend applica limiti di sicurezza già previsti.
2. Il flusso crea/riusa la `SupportRequest` appropriata e produce un riepilogo del ticket che distingua **problema riportato**, **verifiche effettivamente tentate**, **esito**, **incertezze** e **fonti KB consultate**. Se mancano dati, riportare «non noto», non colmare i vuoti.
3. Creare il ticket tramite servizio/adapter mock transazionale e persistente; registrare `ticket_created` e relativi eventi audit con ID di correlazione, timestamp ed errori senza contenuti sensibili.
4. Restituire al dipendente **ID e stato del ticket solo dopo commit riuscito**. Su errore, comunicare che la creazione non è confermata, conservare la richiesta e consentire retry senza duplicati.
5. Supportare l'interazione successiva del dipendente nella stessa conversazione; eventuali nuovi dettagli pertinenti devono essere persistiti e consultabili dal tecnico, senza riaprire automaticamente o chiudere il ticket.
6. Integrare la consultazione **read-only** degli incidenti noti nel flusso diagnostico quando pertinente, usando soltanto campi minimizzati e sanificati; timestamp sempre presenti, senza escludere incidenti vecchi per sola età. Se un incidente è già noto, suggerire correlazione ed evitare escalation ridondanti **solo quando giustificato**, mai impedire la richiesta esplicita di assistenza.

### C. API tipizzate e dashboard tecnico minima

1. Esporre endpoint per elenco/dettaglio ticket, note, aggiornamento stato, elenco/dettaglio incidenti e conferma/rimozione collegamento incidente. Filtri/paginazione e codici HTTP coerenti (`404`, `409`, `422`, `503` se applicabile). Non esporre dati sensibili o intere conversazioni nei listati.
2. La vista Tecnico mostra ticket reali con **stato, sintesi, data aggiornamento e riferimento richiesta**; selezionando un ticket mostra diagnosi, passi tentati, fonti, note e timeline. Possibilità di aggiungere note e aggiornare stato con conferma esplicita.
3. Le azioni del tecnico aggiornano database e audit; la vista Dipendente può mostrare stato corrente del ticket collegato, senza falsi aggiornamenti in tempo reale.
4. Fornire un set piccolo e documentato di **incidenti mock** per dimostrare correlazioni, mantenendolo separato dai dati reali delle conversazioni e con seed idempotente. Consentire il collegamento manuale, non il merge automatico.
5. L'UI deve avere alto contrasto, spaziatura e gerarchia visiva; dettagli su richiesta, niente tabelle sovraccariche, glass effect selettivo. Non introdurre login per ruolo o account amministratore.

### D. Affidabilità e sicurezza

- Redigere e sanificare note, riepiloghi e campi degli incidenti; non inserire password, token o API key in ticket, log, output Gemini o mock. Verificare la redazione anche su dati provenienti dall'LLM.
- Non fidarsi di output LLM o di testo KB/incidenti per autorizzare mutazioni; validare schema, ID, transizioni e parametri delle operazioni.
- Audit oggettivo di creazione, modifica stato, aggiunta note, collegamento incidente ed errori; non ricostruire retroattivamente eventi inesistenti.
- Gestire retry, timeout Gemini, errori DB, richieste duplicate e aggiornamenti concorrenti; evitare stati parziali (ticket presente senza legame alla richiesta, UI che annuncia ticket inesistente).
- Preservare le API G01–G04 e dati esistenti. Documentare esplicitamente che lo switch tra viste **non** costituisce un controllo di accesso in un deployment pubblico.

## 3. Test obbligatori (deterministici, senza chiamate Gemini reali)

| Ambito | Verifiche minime |
|---|---|
| Schema/migrazioni | Migrazione su DB G02–G04 popolato, vincoli FK, indici, restart, rollback senza perdita dati |
| Escalation | Esplicita e suggerita; riepilogo coerente; creazione ticket + audit; messaggio di conferma solo dopo commit |
| Idempotenza/concorrenza | Doppio click, retry dopo timeout, richieste simultanee: nessun ticket duplicato accidentale |
| Failure handling | Gemini indisponibile → fallback etichettato; DB/adapter fallito → nessun falso ticket o conferma |
| Stato ticket | Transizioni valide, invalide `409`, note persistenti, audit e timeline ordinata, riapertura controllata |
| Incidenti | Seed idempotente, ricerca read-only minimizzata, collegamento confermato, nessun merge automatico, incidenti datati visibili |
| Sicurezza | Note con segreti, prompt injection nel riepilogo/incidenti, ID non validi, input troppo lunghi, nessuna mutazione da testo LLM |
| UI | Ticket visibile dopo escalation, dettaglio e note, cambio stato, aggiornamento dopo reload, empty/error state, accessibilità essenziale |
| Regressione | `make check`, pytest, Vitest, Ruff, mypy, ESLint, type-check e build senza regressioni |

Usare stub Gemini e DB temporanei nei test; smoke test reali Gemini **separati e opt-in**, con quota limitata. Non confondere fixture e prova end-to-end reale.

## 4. Scenario di accettazione end-to-end

1. Avviare l'app con dati preesistenti G01–G04 e incidenti demo; verificare che le conversazioni esistenti siano intatte.
2. Nella vista Dipendente aprire una conversazione, descrivere un problema email e chiedere esplicitamente un tecnico (oppure arrivare a escalation dopo troubleshooting).
3. Verificare che la `SupportRequest` esista, che il **ticket mock sia creato realmente**, e che il chatbot mostri ID/stato solo dopo successo.
4. Passare alla vista Tecnico: il ticket appare nell'elenco; aprire il dettaglio e confrontare sintesi, passi tentati e fonti con la conversazione effettiva.
5. Aggiungere una nota tecnica e passare `open → in_progress`; verificare timeline e audit.
6. Consultare un incidente mock pertinente e collegare manualmente il ticket; verificare che la richiesta originale resti distinta e che il collegamento sopravviva al riavvio.
7. Riavviare backend e ricaricare frontend: ticket, stato, note, incidente e conversazione devono persistere.
8. Ripetere la richiesta di escalation / simulare retry: nessun duplicato accidentale; simulare errore DB e verificare assenza di conferme false.
9. Verificare il caso **risolto dal bot senza escalation**: rimane una `SupportRequest` con esito appropriato, **nessun ticket**. La generazione di proposte KB è riservata a G06.

## 5. Definition of Done

GOAL 05 è **DONE** soltanto se:

- [ ] Tutti i deliverable A–D sono integrati, senza anticipare chat tecnico AI o pubblicazione KB (G06).
- [ ] Migrazioni e dati G01–G04 preservati; API precedenti compatibili.
- [ ] Escalation → ticket → vista Tecnico → nota/stato → incidente collegato → restart funziona davvero.
- [ ] Failure, concorrenza, idempotenza, redazione, transizioni e audit sono coperti da test passanti.
- [ ] `make check` e build completi passano, con comandi ed esiti riportati.
- [ ] Scenario browser/API end-to-end verificato, distinguendo test reali da mock e fallback.
- [ ] README e `.env.example` aggiornati solo se necessario, senza segreti; limiti di sicurezza del demo switch esplicitati.
- [ ] Report finale sintetico con file modificati, test eseguiti, limiti e stato `DONE`/`INCOMPLETO`.

**Modalità operativa:** leggere `AGENTS.md` e il repository prima di agire; pianificare brevemente, poi procedere in autonomia fino ai criteri di fine. Correggere i problemi riscontrati senza allargare lo scope. Chiedere chiarimenti solo per decisioni realmente bloccanti o rischiose.
