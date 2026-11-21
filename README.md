# Service Desk AI Assistant — Prototipo Locale

Assistente IT interno per il supporto e la diagnosi autonoma delle problematiche aziendali ricorrenti (500 dipendenti).  
Il repository implementa le fondazioni e la persistenza locale secondo le specifiche di **GOAL 01** e **GOAL 02**.

---

## 1. Prerequisiti

- **Linux / macOS / WSL2**
- **Python:** 3.11+ (testato su Python 3.12.3)
- **Node.js:** 18+ o 20+ (testato su Node v20.20.2 e npm 10.8.2)
- Nessun database server esterno, servizio cloud o chiave API Gemini richiesti per eseguire, migrare o testare G01/G02.

---

## 2. Struttura del Repository

```
.
├── .env.example          # Template delle variabili d'ambiente (backend e frontend)
├── .gitignore            # Regole di esclusione per cache, log, DB, venv, node_modules
├── Makefile              # Comandi unificati (make test, make lint, make check, make migrate)
├── README.md             # Questa guida rapida
├── alembic.ini           # Configurazione migrazioni database Alembic
├── backend/
│   ├── alembic/          # Script e versioni di migrazione dello schema
│   │   ├── env.py
│   │   └── versions/
│   │       └── 001_initial_schema.py # Migrazione iniziale tabelle G01/G02
│   ├── app/
│   │   ├── api/
│   │   │   ├── health.py         # GET /api/health
│   │   │   ├── conversations.py  # CRUD conversazioni, messaggi e richieste
│   │   │   └── requests.py       # Consultazione richieste IT (vista tecnico)
│   │   ├── core/
│   │   │   ├── redaction.py      # Sanitizzazione automatica password e token
│   │   │   └── audit.py          # Helper per emissione sincrona di AuditEvent
│   │   ├── db/
│   │   │   ├── base.py           # DeclarativeBase e SchemaBootstrap
│   │   │   ├── models.py         # Modelli Conversation, Message, SupportRequest, AuditEvent
│   │   │   └── session.py        # SQLite Engine, PRAGMA foreign_keys=ON, runner migrazioni
│   │   ├── schemas/              # Schemi Pydantic tipizzati per request/response
│   │   ├── config.py             # Settings tipizzati con Pydantic
│   │   └── main.py               # FastAPI application e CORS
│   └── tests/                    # Suite completa test unitari, integration e persistenza
├── frontend/
│   ├── src/
│   │   ├── api/client.ts         # Client HTTP tipizzato verso il backend
│   │   ├── components/
│   │   │   ├── Header.tsx        # Header, brand e status badge
│   │   │   ├── ViewSwitch.tsx    # Switch Dipendente / Tecnico
│   │   │   ├── ConnectionBadge.tsx # Indicatore connessione API e DB
│   │   │   ├── EmployeeView.tsx  # Vista Dipendente: chat thread e segnalazione problemi
│   │   │   ├── TechnicianView.tsx# Vista Tecnico: tabella richieste IT e filtri
│   │   │   └── NewRequestModal.tsx # Modale per registrazione problemi IT
│   │   ├── hooks/useHealth.ts    # Polling reale stato API
│   │   ├── test/                 # Test Vitest per viste e componenti
│   │   ├── App.tsx               # Shell applicativa principale
│   │   └── main.tsx
│   ├── package.json
│   └── vite.config.ts
└── data/                         # Directory database SQLite persistente
```

---

## 3. Installazione Rapida

### 3.1 Configurazione dell'ambiente
Copiare il file di configurazione d'esempio:
```bash
cp .env.example .env
```

### 3.2 Installazione del Backend (Python)
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

### 3.3 Installazione del Frontend (Node)
```bash
cd frontend
npm install
cd ..
```

---

## 4. Migrazioni del Database

Le migrazioni sono gestite tramite **Alembic** e vengono eseguite automaticamente all'avvio del backend.  
Per applicarle manualmente:
```bash
source .venv/bin/activate
alembic upgrade head
# oppure: make migrate
```

---

## 5. Avvio dei Servizi Locali

### 5.1 Avviare il Backend FastAPI
In un terminale (con il virtualenv attivo):
```bash
source .venv/bin/activate
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
# oppure: make dev-backend
```
- API Health: `http://127.0.0.1:8000/api/health`
- Documentazione interattiva OpenAPI (Swagger): `http://127.0.0.1:8000/docs`

### 5.2 Avviare il Frontend React (Vite)
In un secondo terminale:
```bash
cd frontend
npm run dev
# oppure: make dev-frontend
```
- Interfaccia Web: `http://localhost:5173`

---

## 6. Esecuzione dei Test e Controlli di Qualità

Tutti i test sono **offline, deterministici e non consumano quote esterne**.

### 6.1 Verifica Completa in un Solo Comando
```bash
make check
```
Esegue sequenzialmente:
1. `pytest backend/tests` (51 test passati)
2. `vitest` (14 test passati in 5 test suite)
3. `ruff check backend` (0 errori)
4. `eslint .` (0 errori)
5. `mypy backend` (51 file controllati, 0 errori)
6. `tsc --noEmit` (0 errori)
7. `vite build` (build bundle di produzione)

---

## 7. Knowledge Base e Servizio RAG (GOAL 03)

Il sistema include una base di conoscenza documentale in formato Markdown con Front Matter YAML e un motore di ricerca semantica RAG basato su vettori densi e ChromaDB persistente.

### 7.1 Documenti della Knowledge Base (`knowledge_base/`)
Contiene 8 guide operative approvate (`status: approved`) per i casi d'uso frequenti:
- `reset_password.md`: Procedura self-service (SSPR) e sblocco account bloccato (KB-AUTH-001)
- `email_outlook.md`: Configurazione Outlook desktop/webmail, limiti allegati e quote (KB-MAIL-001)
- `vpn_access.md`: Connessione SecureConnect VPN, split tunneling e certificati (KB-NET-001)
- `wifi_network.md`: Connessione Wi-Fi Corporate 802.1X e Guest portal, diagnostica DHCP (KB-NET-002)
- `mfa_setup.md`: Configurazione Microsoft Authenticator, QR code e number matching (KB-AUTH-002)
- `file_share.md`: Mapping cartelle di rete SMB H: (dipartimento) e S: (scambio) (KB-FILE-001)
- `software_catalog.md`: Installazione Company Portal senza diritti admin e licenze speciali (KB-APP-001)
- `incident_management.md`: Status page disservizi, policy ticket duplicati ed emergenze (KB-OPS-001)
- Documenti di test per filtraggio: `draft_new_printer.md` (`draft`) e `archived_old_vpn.md` (`archived`).

### 7.2 Comandi CLI e Indicizzazione
```bash
# Indicizzazione con encoder deterministico offline (istantaneo, zero download)
make rag-index-fake

# Esecuzione del benchmark di valutazione RAG offline (22 query in italiano)
make rag-eval-offline

# Indicizzazione con modello BGE-M3 locale (richiede download FlagModel)
make rag-index
```

### 7.3 Risultati del Benchmark di Valutazione (Italiano)
Valutazione su `backend/scripts/eval_dataset.json` (22 query realistiche: 21 in-scope, 1 out-of-scope):
- **Recall@5:** 100.0% (21/21 hit nei primi 5 risultati)
- **MRR@5:** 1.0000 (tutti i documenti attesi posizionati al 1° posto)
- **Latenza Media:** ~4.5 ms (P50: 4.5 ms, P95: 6.2 ms)

---

## 8. Contratti API REST Principali

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/health` | Controllo disponibilità backend e connettività SQLite |
| `POST` | `/api/conversations` | Creazione di una nuova conversazione (`title`, `user_id`) |
| `GET` | `/api/conversations` | Elenco thread ordinati per ultimo aggiornamento (paginato) |
| `GET` | `/api/conversations/{id}` | Dettaglio thread con messaggi ordinati e richieste collegate |
| `POST` | `/api/conversations/{id}/messages` | Aggiunta messaggio utente con sanitizzazione segreti |
| `POST` | `/api/conversations/{id}/requests` | Registrazione problema IT associato al thread |
| `GET` | `/api/requests` | Consultazione richieste per i tecnici con filtro per stato |
| `GET` | `/api/requests/{id}` | Dettaglio di una singola richiesta |
| `GET` | `/api/knowledge/status` | Stato indice vettoriale, conteggio documenti/chunk e modello |
| `POST` | `/api/knowledge/search` | Ricerca semantica top_k con supporto multi-query e fusione RRF |
| `POST` | `/api/knowledge/reindex` | Re-indicizzazione manuale e pulizia chunk obsoleti |

---

## 9. Note di Sicurezza e Sanitizzazione

- **Redazione Credenziali:** Prima della persistenza in SQLite o del log strutturato delle query RAG, il modulo `backend/app/core/redaction.py` individua e sostituisce automaticamente pattern espliciti di password (`password: [REDACTED_PASSWORD]`), token Bearer (`Bearer [REDACTED_TOKEN]`), Google API key (`[REDACTED_API_KEY]`) e chiavi private, preservando integralmente il linguaggio naturale ordinario.
- **Sicurezza Path e Dati:** Il parser della Knowledge Base convalida la radice dei file per prevenire directory traversal.
- **Dati Non Attendibili:** Il testo recuperato dalla KB è marcato e trattato come dato di contesto non eseguibile, garantendo la separazione da future istruzioni di sistema.

