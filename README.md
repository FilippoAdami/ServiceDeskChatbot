# Service Desk AI Assistant — Prototipo Locale

Assistente IT interno per il supporto e la diagnosi autonoma delle problematiche aziendali ricorrenti (500 dipendenti).  
Questo repository implementa la base locale, modulare e testata secondo le specifiche di **GOAL 01**.

---

## 1. Prerequisiti

- **Linux / macOS / WSL2**
- **Python:** 3.11+ (testato su Python 3.12.3)
- **Node.js:** 18+ o 20+ (testato su Node v20.20.2 e npm 10.8.2)
- Nessun database server, servizio cloud o API key esterna richiesti per avviare o testare G01.

---

## 2. Struttura del Repository

```
.
├── .env.example          # Template delle variabili d'ambiente (backend e frontend)
├── .gitignore            # Regole di esclusione per cache, log, DB, venv, node_modules
├── README.md             # Questa guida rapida
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── health.py # Endpoint GET /api/health tipizzato
│   │   ├── config.py     # Impostazioni centralizzate con validazione Pydantic
│   │   ├── db/
│   │   │   ├── base.py   # DeclarativeBase SQLAlchemy e tabella bootstrap
│   │   │   └── session.py# Engine SQLite persistente, session factory e check connessione
│   │   └── main.py       # FastAPI application, CORS ristretto e lifespan
│   ├── tests/            # Test suite offline per health, DB persistenza e config
│   ├── pyproject.toml    # Configurazione di pytest, ruff e mypy
│   ├── requirements.txt  # Dipendenze runtime di produzione
│   └── requirements-dev.txt # Dipendenze per test e qualità
├── frontend/
│   ├── src/
│   │   ├── components/   # Header, ViewSwitch, ConnectionBadge, Placeholders
│   │   ├── hooks/        # useHealth (interrogazione reale API HTTP)
│   │   ├── types/        # Tipi TypeScript per risposte API
│   │   ├── test/         # Test Vitest per switch viste e badge connessione
│   │   ├── App.tsx       # Shell applicativa responsive
│   │   └── main.tsx      # Entry point React
│   ├── package.json      # Script e dipendenze React, Vite, Tailwind, Vitest, Motion
│   ├── vite.config.ts    # Configurazione Vite con proxy /api verso 127.0.0.1:8000
│   └── tailwind.config.js# Design system moderno e ad alto contrasto
└── data/                 # Directory creata automaticamente per il database SQLite
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

## 4. Avvio dei Servizi Locali

### 4.1 Avviare il Backend FastAPI
In un terminale (con il virtualenv attivo):
```bash
source .venv/bin/activate
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
- API Health: `http://127.0.0.1:8000/api/health`
- Documentazione interattiva OpenAPI (Swagger): `http://127.0.0.1:8000/docs`

### 4.2 Avviare il Frontend React (Vite)
In un secondo terminale:
```bash
cd frontend
npm run dev
```
- Interfaccia Web: `http://localhost:5173`
- La shell si connette in tempo reale all'API FastAPI e visualizza lo stato del database SQLite (`DB Attivo`) e la latenza in millisecondi.

---

## 5. Esecuzione dei Test e Controlli di Qualità

Tutti i test sono **offline, deterministici e non consumano quote esterne**.

### 5.1 Test Backend (Pytest, Ruff, Mypy)
```bash
source .venv/bin/activate

# Esecuzione test unitari e di persistenza SQLite
PYTHONPATH=. pytest backend/tests

# Linting del codice backend
ruff check backend

# Controllo statico dei tipi
mypy backend
```

### 5.2 Test Frontend (Vitest, ESLint, TypeScript, Build)
```bash
cd frontend

# Test unitari dei componenti e del cambio vista (Vitest)
npm test

# Linting ESLint
npm run lint

# Type checking TypeScript
npm run type-check

# Build di produzione
npm run build
```

---

## 6. Porte e Indirizzi di Default

| Servizio | URL / Indirizzo | Descrizione |
|---|---|---|
| **Frontend UI** | `http://localhost:5173` | Applicazione React con switch Dipendente/Tecnico |
| **Backend API** | `http://127.0.0.1:8000/api/health` | Endpoint JSON tipizzato di stato |
| **OpenAPI Docs** | `http://127.0.0.1:8000/docs` | Documentazione Swagger automatica |
| **SQLite DB** | `./data/service_desk.db` | File persistente creato automaticamente |

---

## 7. Variabili di Configurazione (.env)

| Variabile | Default | Descrizione |
|---|---|---|
| `ENVIRONMENT` | `development` | Nome ambiente di runtime (`development`, `test`, `production`) |
| `DATABASE_URL` | `sqlite:///./data/service_desk.db` | Connessione database SQLite persistente |
| `CORS_ORIGINS` | `http://localhost:5173,...` | Origini ammesse per le richieste cross-origin |
| `GEMINI_API_KEY` | *(vuoto)* | Opzionale per G01; gestito unicamente lato server |
| `VITE_API_URL` | `http://localhost:8000` | URL del backend per il proxy di sviluppo |

---

## 8. Risoluzione dei Problemi Comuni (Troubleshooting)

- **Porta 8000 già occupata:**  
  Avviare uvicorn su una porta alternativa (es. `--port 8001`) e aggiornare `VITE_API_URL` in `.env` e nel file `frontend/vite.config.ts`.
- **Errore di import `backend` con pytest:**  
  Assicurarsi di eseguire `PYTHONPATH=. pytest backend/tests` dalla directory root del progetto.
- **Badge API Offline nel browser:**  
  Verificare che il server FastAPI sia attivo sulla porta 8000 e che `curl -i http://127.0.0.1:8000/api/health` restituisca HTTP 200.
