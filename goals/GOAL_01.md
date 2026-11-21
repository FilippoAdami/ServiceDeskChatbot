# GOAL 01 — Fondazioni eseguibili e verificabili

## Obiettivo
Da repository vuoto o esistente, ottenere una **base locale avviabile e testata**: React + Vite comunica con FastAPI, SQLite è persistente, configurazione e segreti sono separati dal codice, e la pipeline di verifica funziona. **Non** implementare ancora il chatbot, RAG, ticketing o dashboard operativa.

L'agente ha autonomia su organizzazione interna, naming e piccoli dettagli implementativi, rispettando `AGENTS.md` e senza introdurre complessità non richiesta.

## Deliverable richiesti
1. **Frontend** React + Vite + TypeScript con Tailwind CSS, predisposizione shadcn/ui, Lucide e Motion; shell responsive con switch visivo **Dipendente / Tecnico** e placeholder chiari. Design leggibile e contrastato; niente dashboard fittizia densa.
2. **Backend** FastAPI con `GET /api/health` che restituisce JSON tipizzato (es. `{"status":"ok"}`), documentazione OpenAPI e CORS ristretto all'origine locale di sviluppo.
3. **Persistenza** SQLAlchemy + SQLite: inizializzazione schema minima e un controllo reale della connessione DB. Non definire ora tutto il modello dati: predisporre il layer DB e una strategia semplice per evolvere lo schema.
4. **Configurazione** centralizzata via environment: URL/origini, percorso DB, chiave Gemini e nomi modello come valori configurabili; `.env.example` senza segreti, `.gitignore` per env, DB, indici, build e cache. La chiave Gemini **non è richiesta per avviare G01**.
5. **Qualità**: comandi riproducibili per installare, avviare e verificare frontend e backend; test backend con pytest e test frontend essenziali con Vitest/Testing Library (o equivalente motivato), lint e type-check. Evitare dipendenze che richiedono servizi esterni.
6. **Documentazione**: README breve con prerequisiti, comandi esatti, porte, struttura, variabili e troubleshooting essenziale. Non creare altra documentazione estesa.

## Criteri di accettazione — tutti obbligatori
- [ ] Da checkout pulito, installazione e avvio documentati funzionano su ambiente locale Linux; nessun servizio cloud, database server o chiave API necessari.
- [ ] Frontend raggiungibile nel browser, responsive e con switch Dipendente/Tecnico funzionante; la vista cambia senza reload e non mostra dati o capacità non ancora implementati.
- [ ] Il frontend effettua una **vera richiesta HTTP** a FastAPI e visualizza uno stato di connessione coerente (online/errore), non hardcoded.
- [ ] `GET /api/health` risponde HTTP 200 con payload valido; è verificato da test automatico.
- [ ] SQLite viene creato nel percorso configurato e la connessione è verificata; un riavvio non elimina il file o i dati di una fixture di test.
- [ ] La configurazione fallisce in modo chiaro per valori invalidi; nessuna API key è esposta nel bundle frontend o committata.
- [ ] Backend: pytest passa. Frontend: test passa, lint passa, type-check e build di produzione passano.
- [ ] Sono coperti almeno: health success, health/DB failure o configurazione DB invalida, switch viste, indicatore API disponibile/non disponibile. I test sono offline e deterministici.
- [ ] README permette a un altro sviluppatore di riprodurre tutto senza spiegazioni orali.
- [ ] Nessun chatbot simulato, nessuna chiamata Gemini, nessun ticketing/RAG e nessuna falsa funzionalità vengono introdotti in questa milestone.

## Verifica finale richiesta all'agente
Eseguire e riportare i **comandi effettivi** per: test backend, test frontend, lint, type-check, build frontend, avvio/smoke test API, prova di connessione dal frontend. Se un controllo browser non è automatizzabile, dichiarare esplicitamente la verifica manuale necessaria e non affermare che sia passato.

**Definition of Done:** tutti i criteri precedenti verificati e nessun test fallito. In caso contrario, consegnare stato `INCOMPLETO` con blocchi precisi e istruzioni di recupero.
