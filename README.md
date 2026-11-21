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
1. `pytest backend/tests` (34 test passati)
2. `vitest` (14 test passati in 5 test suite)
3. `ruff check backend` (0 errori)
4. `eslint .` (0 errori)
5. `mypy backend` (32 file controllati, 0 errori)
6. `tsc --noEmit` (0 errori)
7. `vite build` (build bundle di produzione)

---

## 7. Contratti API REST Principali (G02)

| Metodo | Endpoint | Descrizione |
|---|---|---|
| `GET` | `/api/health` | Controllo disponibilità backend e connettività SQLite |
| `POST` | `/api/conversations` | Creazione di una nuova conversazione (`title`, `user_id`) |
| `GET` | `/api/conversations` | Elenco thread ordinati per ultimo aggiornamento (paginato) |
| `GET` | `/api/conversations/{id}` | Dettaglio thread con messaggi ordinati e richieste collegate |
| `POST` | `/api/conversations/{id}/messages` | Aggiunta messaggio utente (`role="user"`) con sanitizzazione segreti |
| `POST` | `/api/conversations/{id}/requests` | Registrazione problema IT associato al thread |
| `GET` | `/api/requests` | Consultazione richieste per i tecnici con filtro per stato |
| `GET` | `/api/requests/{id}` | Dettaglio di una singola richiesta |

---

## 8. Note di Sicurezza e Sanitizzazione

- **Redazione Credenziali:** Prima della persistenza in SQLite, il modulo `backend/app/core/redaction.py` individua e sostituisce automaticamente pattern espliciti di password (`password: [REDACTED_PASSWORD]`), token Bearer (`Bearer [REDACTED_TOKEN]`), Google API key (`[REDACTED_API_KEY]`) e chiavi private, preservando integralmente il linguaggio naturale ordinario.
- **Audit Logging:** Ogni azione (`conversation_created`, `message_sent`, `support_request_created`) produce un `AuditEvent` sincrono con payload sanificato (mai testi integrali dei messaggi né credenziali).
