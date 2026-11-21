---
id: KB-FILE-001
title: Accesso a Cartelle di Rete Condivise (File Share) e Mapping Unità
category: File e Archiviazione
tags:
  - file share
  - cartelle di rete
  - smb
  - sharepoint
  - nas
  - permessi
  - mapping
status: approved
version: 1.1
last_updated: "2026-10-14"
author: IT Operations Team
summary: "Connessione alle cartelle di rete aziendali (dischi H: dipartimentale e S: comune), mapping manuale e richiesta permessi."
---

# Accesso a Cartelle di Rete Condivise (File Share) e Mapping Unità

L'infrastruttura di archiviazione file dell'azienda mette a disposizione cartelle condivise su server NAS/SAN ad alta affidabilità con snapshot orari e backup geografico.

## Struttura delle Unità Condivise

Sui personal computer dei collaboratori sono solitamente mappate due unità di rete principali:
- **Unità H: (Home / Dipartimento):** Cartella riservata al tuo team o reparto aziendale (es. `\\nas01.azienda.local\dept$\Amministrazione`). L'accesso è ristretto ai membri autorizzati del gruppo Active Directory del dipartimento.
- **Unità S: (Shared / Scambio comune):** Cartella aperta a tutto il personale per lo scambio rapido di file e documenti temporanei (es. `\\nas01.azienda.local\shared`). I file non modificati da oltre 90 giorni in quest'area vengono archiviati automaticamente.
- **Cartelle Progetto:** Spazi dedicati a gruppi interdisciplinari (es. `\\nas01.azienda.local\projects$\NomeProgetto`).

## Come Connettere Manualmente una Cartella di Rete (Mapping Drive)

Se dopo un riavvio o una connessione VPN le cartelle di rete non compaiono in "Questo PC":

### Procedura su Windows:
1. Assicurati di essere in ufficio o connesso alla VPN aziendale.
2. Apri **Esplora File** (tasto Windows + E) e seleziona a sinistra **Questo PC**.
3. Nella barra dei menu in alto seleziona **Connetti unità di rete** (o fai clic destro su Questo PC > Connetti unità di rete).
4. Seleziona la lettera dell'unità (es. `H:` per il dipartimento, `S:` per la cartella di scambio).
5. Nel campo **Cartella**, digita il percorso UNC del server:
   - Dipartimento: `\\nas01.azienda.local\dept$\tuo_dipartimento`
   - Scambio: `\\nas01.azienda.local\shared`
6. Assicurati che siano spuntate le opzioni:
   - "Riconnetti all'avvio"
   - "Connetti con credenziali diverse" (solo se usi un account differente)
7. Clicca su **Fine**.

### Procedura su macOS:
1. Da Finder, premi `Cmd + K` oppure seleziona dal menu in alto **Vai** > **Connessione al server...**.
2. Inserisci l'indirizzo con protocollo SMB: `smb://nas01.azienda.local/shared` oppure `smb://nas01.azienda.local/dept$/tuo_dipartimento`.
3. Inserisci nome utente (`azienda\nome.cognome`) e password aziendale.
4. Spunta l'opzione "Memorizza password nel portachiavi".

## Errore "Accesso negato" o "Autorizzazioni insufficienti"

Se visualizzi il messaggio di errore: *"Impossibile accedere a \\nas01\... L'utente non dispone delle autorizzazioni necessarie"*:
1. Verifica che la sessione Kerberos sia valida disconnettendoti e riconnettendoti al sistema operativo Windows.
2. L'accesso alle cartelle riservate richiede l'appartenenza a specifici gruppi di sicurezza Active Directory.
3. Se hai cambiato reparto o hai bisogno di accedere ai file di un altro dipartimento, è necessario che il tuo Responsabile di Unità invii un'approvazione al Service Desk tramite ticket indicando il percorso esatto della cartella e il livello di accesso richiesto (Sola Lettura o Lettura/Scrittura).
