---
id: KB-AUTH-001
title: Procedura di Reset Password e Policy Account
category: Account e Accessi
tags:
  - password
  - reset
  - account
  - active directory
  - credenziali
  - blocco
status: approved
version: 1.2
last_updated: "2026-10-15"
author: IT Security Team
summary: Guida al reset self-service della password, requisiti di complessità e procedura per account bloccato.
---

# Procedura di Reset Password e Policy Account

La presente guida descrive le modalità di modifica e ripristino della password per gli account aziendali del personale (Active Directory / Microsoft 365) e la procedura in caso di account bloccato.

## Requisiti di Complessità della Password

La password aziendale deve rispettare le seguenti regole di sicurezza:
- Lunghezza minima: almeno 12 caratteri (consigliati 16).
- Deve contenere almeno tre delle seguenti categorie: lettere maiuscole (A-Z), lettere minuscole (a-z), numeri (0-9), caratteri speciali (!@#$%^&*-_+=?).
- Non può contenere il nome o cognome dell'utente o il nome dell'azienda.
- Non è possibile riutilizzare le ultime 5 password impostate in precedenza.
- La validità massima della password è di 90 giorni; riceverai un promemoria via email 14 giorni prima della scadenza.

## Procedura di Reset Self-Service (SSPR)

Se ricordi la password attuale o se hai configurato i metodi di recupero Microsoft Authenticator / SMS:

1. Apri il browser e collegati al portale aziendale: `https://passwordreset.microsoftonline.com` oppure al portale intranet `https://id.azienda.local/reset`.
2. Inserisci il tuo indirizzo email aziendale completo (es. `nome.cognome@azienda.it`) e risolvi il captcha di sicurezza.
3. Seleziona il metodo di verifica desiderato:
   - Notifica sull'app Microsoft Authenticator installata sullo smartphone aziendale o personale registrato.
   - Codice numerico a 6 cifre inviato via SMS sul numero di cellulare certificato.
4. Digita la nuova password due volte rispettando i requisiti di complessità.
5. Clicca su **Fine**. La sincronizzazione richiede circa 2 minuti per propagarsi a tutti i sistemi (VPN, Email, PC locale).

## Account Bloccato per Tentativi Errati

Se hai digitato la password errata per più di 5 volte consecutive, l'account viene temporaneamente bloccato per motivi di sicurezza preventiva contro attacchi brute-force.

- **Sblocco automatico:** Il blocco dura 30 minuti. Se non hai urgenza immediata, attendi 30 minuti senza effettuare ulteriori tentativi e riprova con la password corretta.
- **Sblocco tramite Portale Self-Service:** Puoi sbloccare l'account immediatamente autenticandoti con MFA sul portale `https://passwordreset.microsoftonline.com` selezionando l'opzione "Conosco la mia password ma il mio account è bloccato".

## Quando Contattare il Service Desk

Contatta o scala la richiesta al Service Desk IT nei seguenti casi:
- Non hai configurato i metodi di recupero o hai sostituito lo smartphone registrato per l'MFA.
- L'account rimane bloccato anche dopo aver atteso 30 minuti.
- Il portale di reset restituisce l'errore "L'account non è abilitato per la reimpostazione della password".
- Sospetti una violazione di sicurezza o ricevi notifiche di accesso non autorizzate.

In caso di escalation, un tecnico IT verificherà l'identità dell'utente tramite videochiamata interna o chiamata al numero certificato HR prima di generare un Temporary Access Pass (TAP).
