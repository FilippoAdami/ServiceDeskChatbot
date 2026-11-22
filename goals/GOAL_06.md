# GOAL 06 — Assistente tecnico e ciclo di miglioramento della Knowledge Base

**Stato:** da implementare  
**Prerequisiti:** GOAL 01–05; prima di intervenire verificare nel repository migrazioni, contratti API, orchestratore Gemini, RAG reale e suite `make check`.  
**Obiettivo:** chiudere il ciclo di conoscenza del Service Desk: il tecnico dialoga con un assistente AI **contestualizzato al ticket**, registra interventi e conferma l'esito; sia le richieste **risolte dal bot** sia i **ticket risolti dal tecnico** possono produrre una **proposta KB** revisionabile. Solo l'approvazione esplicita pubblica Markdown valido e aggiorna l'indice RAG persistente. Il nuovo contenuto deve risultare effettivamente recuperabile.

## 1. Confini e invarianti

- **Non creare un secondo sistema agentico indipendente:** riutilizzare provider Gemini, configurazione, strumenti RAG, logging, budget e validazione già presenti. La chat tecnico ha prompt/contesto e permessi differenti dalla chat dipendente; non riutilizzare indiscriminatamente la conversazione dell'utente.
- **Separare fatti, proposte e mutazioni:** il modello può sintetizzare note e proporre stato/soluzione/bozza KB; solo azioni esplicite e validate dal backend modificano ticket o documentazione. Un messaggio «ora funziona» non chiude automaticamente il ticket. Nessuna pubblicazione autonoma.
- **Origini distinte:** `SupportRequest` risolta dal bot (preferibilmente `resolved_confirmed`) oppure `Ticket` risolto e documentato dal tecnico. Una risposta proposta ma non confermata non è una risoluzione verificata. Non inventare passaggi, cause, verifiche o conferme.
- **Knowledge Base come fonte controllata:** documenti Markdown con front matter YAML, status `draft`/`approved`, ID/versione, categoria e provenienza. Solo `approved` entra nell'indice. Evitare credenziali, dati personali e riferimenti specifici al singolo dipendente.
- **Revisione umana obbligatoria:** il tecnico può modificare la bozza, approvarla, rifiutarla o richiedere una nuova generazione. Controllo duplicati/similarità con scelta esplicita tra nuova guida e aggiornamento di guida esistente; nessun overwrite silenzioso.
- **Ambiente demo locale:** switch Dipendente/Tecnico senza autenticazione reale; non esporre pubblicamente endpoint di approvazione/pubblicazione. Nessun account admin, servizi cloud aggiuntivi, code distribuite o workflow enterprise.
- **Rinviare a G07:** hardening finale trasversale, test completi della demo, rifinitura UX estesa, deployment eventuale. G06 deve comunque consegnare una UI utilizzabile e testata.

## 2. Deliverable

### A. Assistente AI contestualizzato al ticket

1. Nel dettaglio ticket della vista Tecnico aggiungere una **chat tecnica dedicata**, con messaggi persistenti, autore e timestamp, distinta dai messaggi della conversazione dipendente. Riprendibile dopo refresh/riavvio.
2. Il backend fornisce all'assistente il contesto minimo autorizzato: riepilogo ticket, stato, note/attività, passi già tentati, fonti KB, incidenti collegati e timestamp; non trasferire segreti o intere conversazioni senza necessità.
3. L'assistente può aiutare a diagnosticare, consultare la KB, riassumere gli interventi descritti e **proporre** aggiornamenti strutturati (nota, rilievo, causa, soluzione, stato). Il tecnico vede una preview e **conferma** prima che il backend applichi cambiamenti.
4. Riutilizzare la macchina a stati G05 e l'audit oggettivo: nota, transizione e conferma sono eventi distinti. Una risposta AI non prova che il servizio sia ripristinato; mantenere le incertezze.
5. Gestire Gemini indisponibile, timeout, output invalido e limiti di quota: chat tecnica con errore esplicito, ticket sempre consultabile e aggiornabile **manualmente**, nessuna mutazione fantasma.

### B. Proposte di Knowledge Base da entrambe le origini

1. Aggiungere entità persistente `KnowledgeProposal` (o equivalente) con ID, `source_type` (`support_request`/`ticket`), source ID, stato (`draft`, `approved`, `rejected`, eventuale `failed`/`publishing`), titolo, contenuto Markdown/YAML o campi strutturati, destinazione (`create`/`update`), riferimento KB target, versione, autore demo, timestamps e audit. Migrazione Alembic compatibile con dati G01–G05.
2. **Origine bot:** quando una `SupportRequest` è `resolved_confirmed` e contiene una soluzione sufficientemente documentata, consentire la generazione di una proposta (automatica al completamento o tramite azione esplicita). Per `resolved_unconfirmed`, `abandoned` o `escalated` non trattare la risoluzione come verificata; eventuale bozza deve essere marcata non verificata e non proposta per approvazione senza revisione sostanziale.
3. **Origine tecnico:** dopo che il tecnico ha documentato interventi ed esito di un ticket `resolved`/`closed`, offrire la generazione di una proposta usando note confermate, riepilogo e cronologia effettiva. La conferma del tecnico sulla risoluzione del ticket non equivale a conferma del dipendente; preservare questa distinzione.
4. Generare una procedura **generalizzabile**, con prerequisiti, sintomi, diagnosi, passi di risoluzione, verifiche ed escalation quando appropriato; distinguere fatti documentati e ipotesi. Evitare riproduzione della chat e dati identificativi. Produrre front matter coerente con parser G03; inizialmente `draft`.
5. Se Gemini fallisce o il contenuto è insufficiente, nessuna bozza apparentemente completa inventata: errore esplicito o bozza manuale incompleta segnalata; l'operatore può sempre redigere manualmente una proposta.
6. Verificare proposte già esistenti per la stessa origine/versione per prevenire duplicazioni involontarie in caso di retry; mantenere possibilità di revisioni intenzionali.

### C. Revisione, deduplicazione, pubblicazione e reindicizzazione

1. Nella vista Tecnico aggiungere una sezione **Proposte KB** con elenco filtrabile, origine, stato, anteprima/editing Markdown e differenza/target quando si aggiorna una guida esistente. Conferma esplicita per approvare, rifiutare e pubblicare.
2. Ricercare documenti KB potenzialmente sovrapposti tramite indice/ricerca esistente (eventuale fallback per titolo/keyword); presentare suggerimenti, **mai** fondere o sovrascrivere automaticamente. Il tecnico decide `create` oppure `update` e verifica il contenuto finale.
3. Validare prima della pubblicazione: YAML/front matter, ID univoco o target esistente, path sicuro entro `knowledge_base/`, versione/status, struttura minima, limiti dimensionali, redazione segreti, assenza di istruzioni pericolose e conformità ai vincoli G03. Non fidarsi del Markdown generato dal modello.
4. Pubblicare il file Markdown `approved` in modo sicuro (scrittura temporanea + replace atomico quando applicabile); preservare la versione precedente negli aggiornamenti o mantenere una storia verificabile. Non cancellare silenziosamente documenti esistenti.
5. Reindicizzare il contenuto approvato tramite il servizio G03 con **lo stesso encoder reale e la stessa configurazione dell'indice**; nessuna contaminazione fake/real. Una proposta approvata deve essere recuperabile da una query pertinente e mantenere source refs corretti. Le bozze/rifiutate non devono comparire nei risultati.
6. **Coerenza in caso di errore:** gestire esplicitamente i casi «file scritto ma indicizzazione fallita» e «indicizzazione riuscita ma aggiornamento DB fallito». Non dichiarare pubblicazione completata se indice e stato non sono coerenti; mantenere stato `failed`/`pending_reindex` recuperabile, retry idempotente e audit. Non è richiesta una transazione distribuita, ma una procedura di riconciliazione affidabile.
7. Prevedere lock/controllo versione o equivalenti per impedire approvazioni simultanee e aggiornamenti concorrenti che perdono modifiche. Non rendere disponibile una guida parzialmente scritta.

### D. API, UI e osservabilità

1. API tipizzate per messaggi della chat tecnico, generazione/lettura/modifica proposta, ricerca duplicati, approvazione/rifiuto, pubblicazione/retry e stato indicizzazione. Validare ID, ownership demo implicita, payload, stati e versioni; errori `404`, `409`, `422`, `503` coerenti.
2. UI tecnica **leggibile e non densa**: nel dettaglio ticket, chat e suggerimenti in pannelli separati; nella sezione KB, lista essenziale e editor/preview con azioni chiaramente distinguibili. Nessuna modifica di stato nascosta dietro una risposta del chatbot.
3. Audit e metriche: `technician_message`, `ticket_update_proposed/confirmed`, `kb_proposal_created/edited/rejected/approved`, `kb_publish_started/succeeded/failed`, `kb_reindexed`, con ID correlati e timestamp UTC. Tracciare tool/latency/token se disponibili, senza testi sensibili nei log.
4. Aggiornare README e `.env.example` soltanto per nuove impostazioni necessarie; mantenere test offline senza chiavi Gemini e smoke test reali **opt-in**, con budget contenuto.

## 3. Test obbligatori (offline deterministici)

| Ambito | Casi minimi da verificare |
|---|---|
| Migrazioni | Upgrade su DB G05 popolato, rollback compatibile, restart, FK e indici; nessuna perdita dati |
| Chat tecnico | Contesto corretto del ticket, persistenza separata dalla chat dipendente, riapertura, timestamp, errori Gemini |
| Proposte AI | Parsing strutturato valido/invalido; niente fatti inventati; redazione; fallback esplicito; nessuna mutazione da sola risposta LLM |
| Origine bot | `resolved_confirmed` produce proposta; `resolved_unconfirmed`, `escalated`, `abandoned` non vengono spacciate per risoluzioni confermate |
| Origine tecnico | Note/interventi confermati → proposta; stato ticket distinto dall'esito della richiesta; ticket senza soluzione sufficiente gestito |
| Revisione | Modifica, rifiuto, approvazione esplicita; controllo duplicati; retry idempotente; conflitto concorrente `409` |
| Pubblicazione | Markdown/YAML validi, status approved, ID/path/versione, scrittura atomica, aggiornamento senza perdita di versione |
| RAG | Bozze escluse; guida approvata recuperabile; reindex idempotente; embedding fake mai mischiati con indice BGE-M3 reale |
| Failure/recovery | Gemini down, Chroma down, scrittura file negata, DB failure, crash fra publish e reindex, retry e riconciliazione |
| Sicurezza | Prompt injection in chat/KB, path traversal, segreti in input/output, dimensioni eccessive, nessuna pubblicazione senza azione tecnica |
| UI | Chat tecnico, preview/confirm, editor KB, reject/approve, error/empty/loading, refresh e restart, contrasto/accessibilità essenziale |
| Regressione | `make check`, pytest, Vitest, Ruff, mypy, ESLint, TypeScript e build senza regressioni G01–G05 |

Usare Gemini stub e encoder finti **solo** nei test deterministici; isolare filesystem, SQLite e Chroma temporanei. La prova di recupero semantico con BGE-M3 reale è **separata e obbligatoria per dichiarare funzionante il RAG reale**, non sostituibile con Recall@5 del fake. Se impossibile per l'ambiente, dichiarare la verifica bloccata e GOAL incompleto rispetto a quel criterio.

## 4. Scenario di accettazione end-to-end

**Percorso A — Risoluzione dal bot senza ticket**
1. Nella vista Dipendente completare una richiesta IT con soluzione documentata e **conferma esplicita dell'utente**; verificare `SupportRequest.resolved_confirmed`, assenza di ticket e dati persistenti.
2. Generare la proposta KB dalla richiesta; nella vista Tecnico aprirla, confrontare i passaggi con le evidenze, modificarla se necessario e approvarla.
3. Pubblicare Markdown `approved`, reindicizzare e cercare un'espressione italiana pertinente: il nuovo documento compare con ID e riferimenti corretti; nessuna bozza compare nei risultati.

**Percorso B — Escalation e risoluzione dal tecnico**
4. Aprire un ticket dalla chat Dipendente, passare alla vista Tecnico, selezionare il ticket e conversare con l'assistente tecnico contestualizzato.
5. Scrivere «Ho verificato X, corretto Y e testato Z: ora funziona»; verificare che l'AI **proponga** nota/esito e che il ticket **non cambi** finché il tecnico non conferma.
6. Confermare nota e transizione consentita verso `resolved`; verificare audit, persistenza e storico.
7. Generare una proposta KB dai fatti confermati, verificarne possibili duplicati, scegliere creazione/aggiornamento, revisionare e approvare.
8. Pubblicare/reindicizzare; verificare nuova ricerca RAG, ripartenza backend e persistenza di ticket, chat tecnica, proposta, file e indice.

**Percorso C — Failure safety**
9. Simulare Gemini non disponibile, output malformato, conflitto di approvazione e errore durante reindex: nessun ticket modificato o KB dichiarata pubblicata senza conferma; il sistema mostra errore e permette recupero senza duplicazioni.

## 5. Definition of Done

GOAL 06 è **DONE** soltanto se:

- [ ] Chat AI del tecnico contestualizzata, persistente e separata dalla chat dipendente; proposta di azioni con conferma esplicita.
- [ ] Proposte KB create sia da risoluzioni bot confermate sia da ticket risolti dal tecnico, senza inventare verifiche o cause.
- [ ] Workflow reale di revisione/editing, controllo duplicati, approvazione/rifiuto e pubblicazione Markdown con reindicizzazione.
- [ ] Documento approvato recuperabile dal RAG reale; bozze e rifiutati esclusi; gestione coerente di versioni e aggiornamenti.
- [ ] Errori, retry, concorrenza, crash parziali, redazione e audit coperti da test; nessuna mutazione implicita dell'LLM.
- [ ] Migrazioni compatibili e dati G01–G05 preservati; API precedenti non regrediscono.
- [ ] `make check` completo e build passanti; scenario A+B+C verificato con distinzione fra stub, smoke reale e verifiche manuali.
- [ ] README aggiornato con istruzioni riproducibili e limitazioni del prototipo locale; report finale con file, comandi/esiti, limiti e stato `DONE`/`INCOMPLETO`.

**Modalità operativa:** leggere `AGENTS.md`, goal corrente e repository; formulare un piano breve, quindi procedere autonomamente. Implementare la soluzione minima robusta, senza anticipare G07. Chiedere chiarimenti solo per scelte bloccanti, distruttive o che comportino costi.
