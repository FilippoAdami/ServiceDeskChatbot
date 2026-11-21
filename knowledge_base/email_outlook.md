---
id: KB-MAIL-001
title: Configurazione Email Aziendale e Risoluzione Problemi Microsoft Outlook
category: Posta e Collaborazione
tags:
  - outlook
  - email
  - posta
  - webmail
  - sincronizzazione
  - exchange
status: approved
version: 1.1
last_updated: "2026-10-20"
author: IT Workplace Team
summary: Configurazione del client Outlook su PC/Mac, accesso webmail e risoluzione mancata ricezione messaggi o crash.
---

# Configurazione Email Aziendale e Risoluzione Problemi Microsoft Outlook

Tutti i dipendenti aziendali hanno a disposizione una casella di posta elettronica gestita su Microsoft 365 Exchange Online. Questa guida copre l'accesso web, la configurazione su client desktop e la diagnostica dei problemi comuni.

## Accesso Webmail (Outlook Web App)

Se il computer aziendale non è disponibile o se il client desktop non si avvia:
1. Accedi da qualsiasi browser all'indirizzo `https://outlook.office.com` o `https://mail.azienda.it`.
2. Inserisci la tua email aziendale (`nome.cognome@azienda.it`) e la password aziendale.
3. Conferma la richiesta di accesso tramite notifica Microsoft Authenticator sullo smartphone.
4. Dalla webmail puoi inviare e ricevere email, accedere al calendario e pianificare riunioni su Microsoft Teams.

## Configurazione del Client Desktop Microsoft Outlook

Sui notebook aziendali con sistema operativo Windows o macOS:

### Procedura Automatica (Consigliata)
1. Avvia l'applicazione **Microsoft Outlook**.
2. Al primo avvio, inserisci il tuo indirizzo email aziendale (`nome.cognome@azienda.it`) e clicca su **Connetti**.
3. Il sistema individuerà automaticamente le impostazioni Exchange tramite protocollo Autodiscover.
4. Quando richiesto, inserisci la password aziendale e completa l'autenticazione a due fattori (MFA).
5. Lascia spuntata l'opzione "Consenti all'organizzazione di gestire il dispositivo" e clicca su **OK**.
6. Al termine, riavvia Outlook per consentire il download iniziale della cache della casella di posta (.ost).

### Parametri Manuali Server (Solo se richiesto per client alternativi)
- Protocollo: Microsoft Exchange / Office 365 (autodiscover consigliato).
- Server IMAP (se abilitato per mobile legacy): `outlook.office365.com`, porta 993, SSL/TLS.
- Server SMTP: `smtp.office365.com`, porta 587, STARTTLS.
- Autenticazione: OAuth2 / Autenticazione moderna obbligatoria.

## Risoluzione Problemi Comuni

### Outlook non invia o non riceve messaggi (Stato: "Disconnesso" o "Tentativo di connessione")
1. Verifica che la connessione internet o la VPN aziendale sia attiva.
2. Controlla in basso a destra nella barra di stato di Outlook: se indica "Lavora non in linea", vai nella scheda **Invio/Ricezione** e clicca su **Lavora non in linea** per disattivarlo.
3. Se lo stato è "Password necessaria", clicca sul messaggio e inserisci le credenziali aggiornate.
4. Svuota la cache di connessione chiudendo Outlook ed eseguendo da riga di comando `outlook.exe /cleanreminders` o riavviando il PC.

### Profilo di Outlook Danneggiato
Se Outlook si chiude all'avvio con messaggio di errore relativo al file di dati:
1. Chiudi Outlook.
2. Apri **Pannello di controllo** > **Posta elettronica (Microsoft Outlook)** > **Mostra profili**.
3. Clicca su **Aggiungi**, nomina il nuovo profilo (es. "Azienda_2026") e segui la procedura guidata inserendo la tua email.
4. Imposta "Utilizza sempre questo profilo" sul nuovo profilo e avvia Outlook.

## Limiti Allegati e Quota Casella
- La dimensione massima per singolo messaggio (inclusi allegati) è di **35 MB**. Per file di dimensioni superiori, carica il file su Microsoft OneDrive / SharePoint e condividi il link con i destinatari.
- Lo spazio massimo standard per casella postale è di **50 GB**. In prossimità del limite riceverai un avviso automatico; archiviare i messaggi obsoleti o contattare l'helpdesk per estensione quota di archiviazione online.
