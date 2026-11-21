# GOAL 02 — Modello dati, persistenza e contratti API

## Obiettivo
Trasformare le fondazioni di G01 in un **backend persistente e verificabile per il ciclo di vita delle conversazioni e delle richieste IT**, con API tipizzate consumabili dal frontend. La milestone prepara RAG, Gemini e ticketing, **senza implementarli**. Il comportamento deve restare corretto dopo il riavvio dell'applicazione.

**Prerequisito:** G01 completato. Prima di intervenire, leggere `AGENTS.md`, `GOAL_01.md`, la documentazione architetturale disponibile e ispezionare il codice reale. Il resoconto di G01 fornito dall'utente è una dichiarazione di completamento, non una verifica indipendente: eseguire i controlli di regressione.

## Confini e decisioni vincolanti
- Conservare stack, struttura e convenzioni esistenti; evitare refactor non necessari. Backend FastAPI + SQLAlchemy + SQLite; frontend React + Vite.
- **Conversation** = thread riapribile; **SupportRequest** = problema IT tracciato anche se risolto senza tecnico; **Ticket** = eventuale escalation successiva; **Incident** = evento condiviso. Non creare ticket per ogni conversazione.
- Una conversazione può contenere **più richieste nel tempo**; una richiesta appartiene a una conversazione. Un messaggio appartiene a una conversazione e può essere associato alla richiesta corrente, se utile. Non assumere che ogni messaggio costituisca una nuova richiesta.
- I ruoli Dipendente/Tecnico restano **viste demo**, senza login o autorizzazione reale. Usare un'identità dipendente dimostrativa stabile e configurata/seedata, non dati personali reali; non dichiarare isolamento multiutente sicuro.
- Timestamp UTC timezone-aware, ID stabili, validazione degli input, errori HTTP coerenti, transazioni atomiche. Non memorizzare segreti in messaggi o log; redazione di pattern comuni prima della persistenza.
- Non generare risposte AI finte: messaggi `assistant` sono ammessi soltanto come fixture nei test, non come output del servizio demo.

## Deliverable

### A. Modello persistente minimo
Definire con SQLAlchemy, tipi e vincoli appropriati:
1. `Conversation`: ID, identificatore demo dell'utente, titolo opzionale, stato (`active`, `waiting_user`, `archived` o equivalenti documentati), `created_at`, `updated_at`.
2. `Message`: ID, conversation ID, ruolo (`user`, `assistant`, `system`/`tool` solo se giustificato), testo, timestamp e ordinamento stabile. API pubbliche di G02 consentono **solo inserimento di messaggi utente**.
3. `SupportRequest`: ID, conversation ID, titolo/descrizione, categoria preliminare e finale opzionali, stato operativo e outcome opzionale; timestamp; spazio per sintesi e risoluzione future. Definire stati coerenti, distinguendo almeno `resolved_confirmed`, `resolved_unconfirmed`, `escalated`, `abandoned` come esiti finali. **Nessuna inferenza di esito dall'inattività.**
4. `AuditEvent` (o equivalente): ID, timestamp UTC, tipo evento, conversation/request ID opzionali, payload minimo e sanificato; generazione **nel momento dell'azione**, non a posteriori.
5. `Ticket` e `Incident`: predisporre **solo schemi/modelli minimi e relazioni necessarie**, se compatibile con una migrazione semplice; nessuna API di creazione ticket, clustering o automazione in G02. Se non necessari ora, documentare i contratti previsti e rinviarne le tabelle a G05.

Garantire chiavi esterne SQLite abilitate, indici utili e cancellazione/archiviazione con semantica esplicita. Non aggiungere campi speculativi.

### B. Evoluzione dello schema
Introdurre una strategia di migrazione riproducibile (preferibilmente **Alembic**, se si integra senza complessità sproporzionata), compatibile con il database bootstrap di G01. Le migrazioni devono essere idempotenti nell'uso previsto e **non cancellare dati esistenti**. Non affidarsi esclusivamente a `create_all()` per evoluzioni future.

### C. API REST tipizzate
Implementare un insieme minimo e coerente, ad esempio:
- `POST /api/conversations`: crea una conversazione demo.
- `GET /api/conversations`: elenco sintetico, ordinato per ultimo aggiornamento, con limite/paginazione.
- `GET /api/conversations/{id}`: dettagli e messaggi ordinati.
- `POST /api/conversations/{id}/messages`: aggiunge **un messaggio utente** e aggiorna `updated_at`; non invoca Gemini.
- `POST /api/conversations/{id}/requests`: registra esplicitamente un nuovo problema IT associato al thread; non classifica automaticamente.
- `GET /api/requests` e `GET /api/requests/{id}`: consultazione delle richieste con filtri essenziali per stato e ordinamento/paginazione.

Gli endpoint sono una proposta di contratto: mantenere eventuali convenzioni già presenti se equivalenti. Usare schemi request/response separati dagli ORM, status HTTP corretti, errori 404/422, e non esporre internals. Non introdurre endpoint generici per cambiare arbitrariamente stati/outcome: eventuali transizioni interne devono essere validate e testate.

### D. Frontend: integrazione minima reale
Sostituire **solo i placeholder strettamente necessari** con una vista dipendente essenziale che permetta di creare/selezionare una conversazione, inviare un messaggio utente, ricaricare e ritrovare la cronologia persistita. Indicare chiaramente che **l'assistente AI non è ancora attivo**; non mostrare risposte automatiche. La vista tecnico può mostrare un elenco **reale** e minimale delle `SupportRequest` presenti, con empty state corretto; la dashboard definitiva è G06. Preservare switch, badge health, design leggibile e test di G01.

### E. Qualità e documentazione
Aggiornare `.env.example` e README solo se necessario; mantenere comandi `make check` / test / lint / type-check / build. Nessun nuovo servizio cloud, nessuna chiamata Gemini, nessun download di modelli embedding.

## Test obbligatori
- **Unit:** validazione schemi, stati/outcome ammessi, transizioni illegali, ordinamento e redazione di segreti comuni (password/token/API key in testo esplicito); verificare che la redazione non distrugga contenuto ordinario.
- **Integration DB/API (SQLite reale temporaneo):** creazione e recupero conversazioni; inserimento e ordine di più messaggi; creazione di una o più richieste nella stessa conversazione; aggiornamento `updated_at`; filtro/paginazione; 404 e 422; rollback atomico su errore; integrità referenziale; eventi audit generati al verificarsi dell'azione.
- **Persistenza:** scrivere dati, chiudere sessione/engine, ricreare l'app o la connessione sullo stesso file e verificare che conversazioni, messaggi, richieste ed eventi siano identici.
- **Migrazioni:** upgrade da schema G01 e ri-esecuzione senza perdita dati; test su DB vuoto e DB bootstrap preesistente.
- **Frontend:** creazione/selezione conversazione, invio messaggio reale via API mockata nei test UI, refresh/ricaricamento e gestione errori/empty state; switch e health G01 non regressi.
- **Regression:** pytest, ruff, mypy, Vitest, ESLint, TypeScript check, Vite build; test ordinari completamente offline.

## Criteri di accettazione — tutti obbligatori
- [ ] G01 continua a passare integralmente, senza regressioni e senza alterazioni non necessarie alla struttura.
- [ ] Modello dati e relazioni rispettano la distinzione Conversation / SupportRequest / Ticket / Incident, senza ticket automatici.
- [ ] Creazione, elenco, lettura e aggiunta di messaggi utente funzionano con API tipizzate e validate; richieste IT create e consultabili separatamente.
- [ ] Più richieste possono appartenere alla stessa conversazione; la cronologia ha ordine deterministico e timestamp UTC validi.
- [ ] Un riavvio reale del backend non perde dati; la migrazione da G01 preserva il bootstrap e funziona su DB vuoto.
- [ ] Input invalidi e ID inesistenti producono errori appropriati; nessuna scrittura parziale in caso di fallimento.
- [ ] Eventi audit sono persistiti al momento delle azioni e non contengono testo integrale dei messaggi o segreti.
- [ ] I segreti comuni presenti nei messaggi sono redatti prima del salvataggio; test specifici verificano il comportamento e i suoi limiti.
- [ ] UI dipendente usa API reali per thread e messaggi; dopo refresh ritrova i dati. Vista tecnico mostra solo dati effettivi/empty state, senza simulare AI o ticket.
- [ ] Nessuna chiamata Gemini, embedding, RAG, ticketing o incident clustering; nessun test richiede rete o API key.
- [ ] Tutti i test, lint, type-check e build passano; README aggiornato con avvio, migrazioni e verifica manuale.

## Verifica finale e Definition of Done
Eseguire e riportare i **comandi effettivi**, output sintetici e risultati per backend/frontend, migrazioni e smoke test HTTP. Eseguire uno scenario dimostrabile: creare conversazione → aggiungere due messaggi → creare richiesta → leggere dalla vista tecnico → riavviare backend → verificare la stessa cronologia. Se il test browser non è automatizzato, indicarlo come **verifica manuale da eseguire**, senza dichiararlo superato.

**DONE** soltanto se tutti i criteri sono verificati. Altrimenti **INCOMPLETO**, con blocchi e test mancanti. Procedere autonomamente fino al goal, senza anticipare G03.
