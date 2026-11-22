# GOAL 04 — Agente conversazionale Gemini e RAG operativo

**Stato:** da implementare  
**Prerequisiti:** GOAL 01–03 completati; verificare repository e test prima di intervenire.  
**Obiettivo:** trasformare la chat persistente in un assistente IT realmente operativo, basato su Gemini e sulla knowledge base locale, senza implementare ancora ticketing automatico, incident correlation o workflow di approvazione KB.

## 1. Contratto architetturale

- **Un solo agente conversazionale**, con tre fasi logiche e istruzioni distinte: **triage**, **diagnosi/risoluzione**, **finalizzazione**. Non creare tre agenti indipendenti né workflow rigidamente categorizzati.
- **Backend autorevole:** conserva messaggi, stato, timestamp UTC, tool call e audit; l'LLM non inventa eventi né modifica direttamente il database.
- **Gemini API reale**, invocata esclusivamente dal backend con chiave da ambiente. Modello configurabile per fase; se il modello o l'SDK differiscono dalle ipotesi, verificare l'API effettiva prima di codificare.
- **RAG locale**: retrieval globale sui documenti `approved`, multi-query quando utile, deduplicazione e citazioni ai chunk; niente filtri rigidi per categoria.
- **Supporto aziendale soltanto**: rifiutare con cortesia richieste estranee; non inventare policy o procedure interne, non eseguire operazioni privilegiate, non chiedere password, OTP o token.
- **Persistenza**: riutilizzare `Conversation`, `Message`, `SupportRequest`, `AuditEvent` e le API G02; introdurre modifiche schema soltanto se motivate, con migrazione Alembic e compatibilità con dati preesistenti.
- **Nessun finto completamento:** distinguere risposte reali da fixture/test; distinguere encoder fake da BGE-M3 reale.

## 2. Deliverable

### A. Adapter Gemini e configurazione

1. Client asincrono o compatibile con FastAPI, isolato dietro interfaccia testabile; timeout, retry **limitati** su errori transitori, gestione rate limit/quota e indisponibilità del provider.
2. Modello, parametri di generazione, eventuale thinking effort e budget configurabili per fase, senza assumere che ogni modello supporti gli stessi parametri.
3. Nessuna chiave API nel frontend, nelle risposte HTTP, nei log o nei test. Avvio e `make check` possibili senza chiave, con test deterministici e mock del provider.
4. Tracciamento di request ID, fase, latenza, token usage se fornito dall'SDK, esito ed error class; mai registrare integralmente contenuti sensibili o prompt con segreti.

### B. Orchestrazione conversazionale

1. Il messaggio utente continua a essere registrato tramite il flusso persistente G02; la risposta dell'assistente viene salvata come `Message(role=assistant)` **solo dopo** generazione riuscita.
2. Stato/fase per conversazione o richiesta, con transizioni esplicite e verificabili; **triage** per chiarire il problema, **diagnosi** per troubleshooting, **finalizzazione** per sintesi strutturata ed esito. La finalizzazione non implica chiusura automatica né conferma di risoluzione.
3. Riutilizzare la cronologia persistita con finestra contestuale e/o sintesi strutturata; evitare crescita illimitata del contesto. La ripresa dopo reload/riavvio non deve perdere lo stato.
4. Gestire messaggi concorrenti sulla stessa conversazione evitando risposte fuori ordine, duplicazioni o stato incoerente; documentare la politica scelta (es. lock per conversazione o HTTP 409).
5. Non duplicare SupportRequest quando una richiesta esiste già; se il problema non è ancora sufficientemente definito, non creare record diagnostici fittizi. Supportare la possibilità di più problemi nella stessa conversazione senza introdurre routing arbitrario.
6. Se l'utente chiede esplicitamente un tecnico, riconoscere l'intento e segnalarlo in modo persistente come **escalation richiesta / da gestire**, senza dichiarare creato un ticket: il ticketing appartiene al goal successivo.

### C. Tool RAG e grounding

1. Collegare l'agente al servizio RAG di G03 tramite un tool/backend service con input validato, `top_k` limitato e risultati compatti: `doc_id`, titolo, sezione, `chunk_id`, testo rilevante e versione/fonte.
2. Retrieval multi-query adattivo: usare varianti complementari per domande ambigue; evitare chiamate inutili per errori specifici. Limitare numero di query, chunk e invocazioni per turno.
3. Restituire all'utente riferimenti leggibili alle procedure effettivamente recuperate; nessuna citazione inventata. I testi recuperati sono **dati non fidati**, non istruzioni per il modello.
4. Se il retrieval non trova fonti adeguate, ammettere l'incertezza e proporre verifiche prudenti o escalation; non inventare configurazioni aziendali.
5. **Validazione embedding reale obbligatoria per dichiarare il RAG operativo:** eseguire indicizzazione e benchmark con BGE-M3, separati da `make rag-eval-offline`. Riportare Recall@5, MRR@5, latenza, hardware e dataset. Non imporre una soglia arbitraria come condizione universale: analizzare gli errori e correggere problemi evidenti prima della chiusura. Se il modello non può essere eseguito, GOAL 04 resta **INCOMPLETO per la validazione end-to-end reale**; non sostituirlo silenziosamente con il fake.

### D. API e UI dipendente

1. Endpoint dedicato all'interazione con l'agente (ad es. `POST /api/conversations/{id}/assistant-turn`) con contratti Pydantic; preservare compatibilità degli endpoint G02. Evitare che il frontend possa inviare `role=assistant` arbitrari.
2. Gestione chiara degli stati `sending`, `thinking`, `retrieving`, `failed` e `ready` **solo quando supportati da eventi reali**; nessuna animazione che faccia credere a tool call inesistenti.
3. Mostrare risposta, riferimenti KB, eventuale messaggio di errore con retry esplicito e storico persistito. Evitare doppio invio accidentale.
4. Se manca la chiave Gemini, UI con stato configurazione non disponibile; nessuna risposta AI simulata in modalità normale.
5. Mantenere UI accessibile, leggibile, poco densa, con glass effect selettivo; non riscrivere la dashboard tecnico di G02.

### E. Sicurezza e limiti operativi

- Redazione dei segreti prima di **persistenza, logging e invio al provider**; non affermare che il riconoscimento regex garantisca la rimozione di ogni segreto. Istruire l'utente a non condividere credenziali.
- Limiti configurabili per lunghezza input, turni, token, query RAG, tool calls e richieste; errori HTTP coerenti (400/409/422/429/502/503 a seconda del caso) senza stack trace o segreti.
- Prompt injection test: un documento KB o un messaggio utente non può sovrascrivere policy, ottenere chiavi, eseguire comandi privilegiati o autorizzare modifiche DB.
- Nessun endpoint operativo per reindexing o strumenti interni deve diventare pubblicamente accessibile senza protezione in un futuro deployment; per G04 mantenere local-first e segnalare nel README i confini di fiducia.

## 3. Test obbligatori

| Area | Prove minime |
|---|---|
| Provider | Successo, timeout, 429/quota, 5xx, risposta vuota/malformata, retry limitato, secret non esposto |
| Fasi | Triage → diagnosi → finalizzazione, ritorno alla diagnosi quando serve, assenza di chiusura automatica |
| Persistenza | Turni utente/assistant salvati e riaperti dopo restart; errori non generano messaggi assistant falsi |
| Concorrenza | Due richieste simultanee sullo stesso thread non corrompono ordine/stato |
| RAG | Tool reale, fonte corretta, nessuna citazione inventata, fallback senza risultati, query deduplicate |
| Sicurezza | Password/token, prompt injection nei documenti, richieste fuori ambito, input lunghi |
| UI | Invio reale, loading/error/retry, visualizzazione fonti, reload e cambio vista |
| Regressione | Tutti i test G01–G03, lint, type-check e build senza regressioni |

I test unit/integration devono usare **mock deterministici del provider Gemini** e, dove appropriato, encoder fake: non devono dipendere da rete, chiavi o consumo di quota. Aggiungere smoke test manuale/opt-in separato con Gemini e BGE-M3 reali.

## 4. Scenario di accettazione end-to-end

1. Configurare `GEMINI_API_KEY` nel backend e indicizzare KB con **BGE-M3 reale**.
2. Aprire una conversazione nella vista Dipendente e chiedere in italiano: «Non riesco ad accedere alla mail aziendale».
3. Verificare che l'assistente faccia triage pertinente, consulti la KB, proponga passaggi coerenti con `KB-MAIL-001`/altre fonti pertinenti e mostri riferimenti realmente restituiti dal retrieval.
4. Rispondere con nuovi dettagli; verificare che l'assistente mantenga il contesto e adatti la diagnosi senza ripartire da zero.
5. Confermare esplicitamente la risoluzione: verificare sintesi/esito coerenti e **nessun ticket creato**.
6. In una seconda conversazione richiedere intervento umano: verificare registrazione dell'intento e comunicazione corretta che il ticketing automatico non è ancora attivo.
7. Ricaricare la pagina e riavviare il backend: conversazioni, messaggi e stati devono restare coerenti.
8. Disattivare temporaneamente l'accesso a Gemini: mostrare errore recuperabile, senza risposta inventata e senza duplicare il turno al retry.

## 5. Definition of Done

GOAL 04 è **DONE** solo quando:

- [ ] Tutti i deliverable A–E sono implementati e integrati senza introdurre ticketing/incident clustering fuori scope.
- [ ] `make check` e test aggiuntivi passano; sono riportati comandi ed esiti effettivi.
- [ ] Test automatici di failure, concorrenza, sicurezza e persistenza passano.
- [ ] Lo scenario end-to-end è verificato con **Gemini reale + BGE-M3 reale** (non solo mock).
- [ ] Sono documentati modelli/configurazioni, metriche retrieval, limiti noti e costi/quota osservati se disponibili.
- [ ] README e `.env.example` sono aggiornati senza includere segreti.
- [ ] L'agente consegna report con file modificati, test, verifiche reali e stato finale `DONE` o `INCOMPLETO`, senza dichiarazioni non verificate.

**Vincoli di esecuzione:** operare autonomamente all'interno del goal; preservare le API e i dati esistenti; preferire cambiamenti piccoli, testabili e reversibili. Se servono credenziali o download modello non disponibili, completare quanto verificabile e segnalare il blocco, senza falsificare lo smoke test reale.
