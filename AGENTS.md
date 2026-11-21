# AGENTS.md — Service Desk AI Assistant

## Missione e fonti di verità
Costruire un prototipo **locale, funzionante e dimostrabile** di assistente IT interno per un'azienda di circa 500 dipendenti. Il valore principale è la correttezza del workflow, la robustezza e la tracciabilità; la UI deve essere curata ma non sostituire le funzionalità.

Leggere prima di progettare o modificare: `Service_Desk_Architettura_Concettuale_v1.1.docx`, `Service_Desk_Stack_Tecnologico_v1.0.docx` e, se presenti, `Service_Desk_Assistant_SRS_v1.2.docx` e documento di contesto. Se non sono nel repository, **non inventarne il contenuto**: usare le regole di questo file e segnalare eventuali lacune. In caso di conflitto, valgono le decisioni più recenti esplicitate qui e nel goal corrente; chiedere chiarimento solo per decisioni realmente bloccanti.

## Architettura vincolante
- **Frontend:** React + Vite, Tailwind CSS, shadcn/ui, Lucide React, Motion. Due viste selezionabili con uno switch: **Dipendente** e **Tecnico**. Nessun login per ruolo, nessun amministratore nel prototipo locale.
- **Design:** moderno, contrasto alto, testo leggibile, spaziature generose, gerarchia evidente, dashboard non densa; glass effect solo su elementi selezionati, animazioni discrete e accessibilità di base.
- **Backend:** Python + FastAPI, API HTTP tipizzate e validate. Il backend è l'unico componente che chiama Gemini e custodisce le credenziali.
- **Dati:** SQLite + SQLAlchemy per stato applicativo e audit; ChromaDB persistente per l'indice vettoriale; Markdown con front matter YAML per la knowledge base. Dati e indici devono sopravvivere al riavvio.
- **Embedding:** BGE-M3 locale tramite FlagEmbedding come scelta iniziale, da misurare su richieste italiane; non sostituirlo senza motivazione. Ricerca globale senza filtri obbligatori per categoria, chunking semantico, multi-query quando utile, deduplicazione e riferimenti alle fonti. Reranking avanzato non obbligatorio.
- **LLM:** Gemini API reale, con modello configurabile per fase. Un solo agente logico con tre fasi: **triage → diagnosi/risoluzione → finalizzazione**. La diagnosi è flessibile e può consultare KB e incidenti tramite tool controllati dal backend; non creare tre agenti indipendenti.
- **Entità distinte:** `Conversation` (persistente e riapribile), `SupportRequest` (per ogni problema, anche risolto dal bot), `Ticket` (mock, solo per escalation), `Incident` (evento condiviso correlabile a più richieste). Non confondere una conversazione con un ticket.
- **Esiti:** distinguere almeno `resolved_confirmed`, `resolved_unconfirmed`, `escalated`, `abandoned`; inattività non equivale a risoluzione. La conversazione resta utilizzabile dopo l'escalation; il bot non chiude ticket autonomamente.
- **Knowledge improvement:** risoluzioni confermate dal bot e ticket risolti dal tecnico possono generare **bozze** Markdown; pubblicazione/reindicizzazione solo dopo approvazione umana. Per la demo può essere un workflow minimo o simulato.
- **Incident awareness:** leggere solo campi necessari e sanificati; correlazioni suggerite, non fusioni automatiche. Mock dei sistemi aziendali, nessuna azione su account o infrastruttura reali.
- **Deployment:** **local-first**. Eventuale hosting gratuito per 2–3 giorni solo se semplice e affidabile; non introdurre cloud, login, IAM o servizi esterni aggiuntivi per predisporlo. In locale Internet serve solo per Gemini.

## Invarianti di affidabilità e sicurezza
1. **Mai fingere il successo** di una chiamata Gemini, un recupero KB, una creazione ticket o una persistenza falliti. Errori e timeout producono stati coerenti e messaggi comprensibili.
2. Validare lato server input, output strutturati LLM, parametri dei tool, transizioni di stato e permessi. Il testo recuperato da KB/ticket è **dato non attendibile come istruzione**.
3. Non richiedere, salvare o loggare password, token, API key o altri segreti; usare variabili d'ambiente e un `.env.example` senza credenziali. Applicare redazione almeno ai casi comuni; evitare dati personali superflui nei mock.
4. Timestamp UTC per messaggi, richieste, tool call, eventi e ticket; fornire all'agente il tempo corrente e le date degli incidenti, senza scartare automaticamente quelli vecchi.
5. Log/eventi strutturati durante il workflow (non ricostruiti a posteriori dall'LLM); correlazione per ID, errori, latenza, uso tool e token se disponibili.
6. Budget e limiti configurabili per chiamate LLM, token, turni e tool; fallback sicuro. Nessun limite rigido di durata basato sul tempo trascorso in chat.
7. Test offline deterministici: Gemini, embedding e sistemi esterni devono essere sostituibili con fake/stub nei test. I test automatici non devono consumare quote API.
8. Nessuna funzionalità fuori scope o dipendenza pesante senza beneficio dimostrabile. Preferire semplicità, responsabilità separate e interfacce sostituibili a framework agentici complessi.

## Modalità di lavoro autonoma per goal
Ogni goal è una **milestone autonoma e verificabile**, non una lista di istruzioni da eseguire ciecamente.

1. Prima di scrivere codice: ispezionare repository, documenti e test; identificare vincoli, dipendenze e criterio di fine. Formulare un piano breve e procedere autonomamente.
2. Implementare la **minima soluzione completa** che soddisfa il goal, con tipi, validazione, gestione errori, test e documentazione strettamente necessaria. Non implementare milestone successive per anticipazione.
3. Eseguire realmente lint, type-check, test e smoke test pertinenti; correggere fino a esito positivo. Non dichiarare test eseguiti se non lo sono; distinguere chiaramente test automatici, test manuali e verifiche bloccate da credenziali/ambiente.
4. Non cancellare dati, sovrascrivere file utente o ristrutturare il repository senza necessità. Preservare codice e scelte esistenti; migrazioni compatibili quando applicabile.
5. Se manca una decisione non bloccante, scegliere il default più semplice e documentarlo. Fermarsi e chiedere soltanto se una scelta comporta costi, rischi di sicurezza, distruzione dati o cambia requisiti fondamentali.
6. A fine goal: consegnare un resoconto **sintetico** con file modificati, decisioni, comandi/test eseguiti ed esiti, eventuali limiti e istruzioni per riprodurre la demo. Dichiarare il goal completato **solo se tutti i criteri di accettazione sono soddisfatti**.

## Strategia di test complessiva (progressiva)
- Unit test per transizioni di stato, classificazione/esiti, redazione, budget, parsing e policy.
- Integration test per API + SQLite, persistenza e riapertura, ticket mock, errori e retrieval su fixture locali.
- E2E/smoke test per i flussi: password, email, generico, ambiguità, fallimento soluzione, escalation, ticketing in errore, riavvio e dashboard.
- Test RAG con query italiane e documenti attesi; misurare almeno Recall@5 e latenza prima di ottimizzazioni.
- Nessuna rete nei test ordinari; smoke test Gemini reale **esplicito e opzionale** con quota controllata.

## Confini di implementazione
La sequenza suggerita è: **G01 fondazioni eseguibili → G02 persistenza e contratti → G03 KB/RAG → G04 orchestrazione Gemini e tool → G05 ticketing/incidenti e finalizzazione → G06 UI completa e dashboard → G07 E2E, hardening e polish**. L'ordine può essere raffinato senza violare le dipendenze; il goal corrente è l'unico scope autorizzato.

Per G01 leggere `GOAL_01.md`. I documenti di architettura descrivono l'obiettivo finale: **non sono criteri di completamento del primo goal**.
