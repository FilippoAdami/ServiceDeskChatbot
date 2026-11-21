---
id: KB-OPS-001
title: Gestione Disservizi Generali, Incidenti IT e Verifica Stato Servizi
category: Operazioni e Incidenti
tags:
  - incidenti
  - disservizio
  - outage
  - status page
  - escalation
  - ticket duplicati
  - emergenza
status: approved
version: 1.1
last_updated: "2026-10-26"
author: IT Service Management Team
summary: Come consultare la pagina di stato dei servizi IT aziendali, verificare incidenti in corso ed evitare aperture multiple.
---

# Gestione Disservizi Generali, Incidenti IT e Verifica Stato Servizi

Durante un malfunzionamento diffuso che coinvolge più persone o interi reparti (ad es. blocco della posta elettronica Exchange, caduta della connettività Internet/VPN, indisponibilità del gestionale SAP), la priorità del team IT è contenere l'impatto e ripristinare il servizio nel minor tempo possibile.

## Come Verificare se un Disservizio è Già Noto (Status Page)

Prima di aprire una nuova richiesta di assistenza individuale o chiamare l'helpdesk:
1. Apri la **Status Page Aziendale** accessibile all'indirizzo `https://status.azienda.it` (raggiungibile anche da smartphone e reti esterne).
2. Nella dashboard principale sono indicati gli stati in tempo reale dei servizi critici:
   - **Verde (Operativo):** Servizio regolarmente funzionante.
   - **Giallo (Degradato):** Rallentamenti o funzionalità parziali.
   - **Rosso (Disservizio / Outage):** Interruzione totale del servizio.
3. Se è presente un banner di **Incidente Maggiore in Corso** relativo al problema che stai riscontrando:
   - L'incidente è già preso in carico dai tecnici e dai fornitori infrastrutturali.
   - Nella pagina dell'incidente sono pubblicati gli aggiornamenti periodici e il tempo stimato di ripristino (ETA).

## Politica sui Ticket Duplicati

Quando un incidente globale è già aperto e classificato:
- **Non aprire ticket duplicati:** L'apertura simultanea di centinaia di ticket individuali per lo stesso problema sovraccarica la coda del Service Desk, rallentando la diagnostica e la risoluzione.
- Se utilizzi l'Assistente AI Service Desk, il bot verificherà automaticamente gli incidenti attivi e collegherà la tua conversazione all'incidente noto, inviandoti gli aggiornamenti senza creare un ticket isolato.

## Quando Segnalare un Nuovo Incidente Grave (P1 / P2)

Se noti un disservizio critico non ancora presente sulla Status Page:
- Contatta immediatamente il Service Desk telefonico di reperibilità al numero interno **5555** (o `+39 02 9999 5555` da cellulare).
- Un incidente è considerato ad alta priorità (P1) se blocca l'operatività di un'intera sede o di un processo produttivo critico (es. fatturazione di fine mese, linea logistica).
- Fornisci: sede/filiale impattata, data e ora di inizio, numero approssimativo di utenti coinvolti ed eventuali messaggi di errore visualizzati.
