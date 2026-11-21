---
id: KB-AUTH-002
title: Configurazione Autenticazione a Due Fattori (MFA) e Gestione Dispositivi
category: Account e Accessi
tags:
  - mfa
  - 2fa
  - microsoft authenticator
  - token
  - otp
  - sicurezza
  - smartphone
status: approved
version: 1.2
last_updated: "2026-10-12"
author: IT Security Team
summary: Guida per configurare Microsoft Authenticator, registrare un nuovo smartphone o ripristinare codici di sicurezza.
---

# Configurazione Autenticazione a Due Fattori (MFA) e Gestione Dispositivi

L'Autenticazione a Più Fattori (MFA - Multi-Factor Authentication) è obbligatoria per tutti gli account aziendali al fine di proteggere dati, email e accessi remoti (VPN e portali cloud).

## Metodi MFA Supportati

La policy aziendale supporta i seguenti metodi di verifica:
1. **Microsoft Authenticator (Consigliato):** Notifica push con verifica del numero (number matching) sullo smartphone. Metodo più rapido e sicuro contro gli attacchi di phishing e fatigue.
2. **Generatore di codice temporaneo (TOTP):** Codice numerico a 6 cifre a rotazione di 30 secondi generato dall'app Microsoft Authenticator o app TOTP compatibile (funziona anche offline e in aereo).
3. **SMS su cellulare certificato (Metodo di emergenza/fallback):** Codice numerico a 6 cifre inviato al numero aziendale o privato registrato su portale HR.
4. **Chiavetta hardware FIDO2 (YubiKey):** Riservata su richiesta formale ad amministratori di sistema o personale che opera in ambienti senza copertura cellulare.

## Configurazione Iniziale su Nuovo Smartphone

Per registrare o riconfigurare Microsoft Authenticator:
1. Da un PC aziendale già autenticato o dalla rete aziendale, accedi a: `https://mysignins.microsoft.com/security-info`.
2. Esegui il login con `nome.cognome@azienda.it` e la password attuale.
3. Clicca su **Aggiungi metodo di accesso** e seleziona **App di autenticazione**.
4. Sul tuo smartphone Android o iPhone, scarica gratuitamente l'app ufficiale **Microsoft Authenticator** dallo store (Google Play Store o Apple App Store).
5. Apri l'app sullo smartphone, seleziona **Aggiungi account** > **Account aziendale o dell'istituto di istruzione** > **Scansiona codice a matrice (QR)**.
6. Inquadra con la fotocamera il codice QR mostrato sullo schermo del PC.
7. L'app genererà un test di verifica: digita sul telefono il numero mostrato sullo schermo del PC per completare l'accoppiamento.
8. Clicca su **Salva**. Il dispositivo è ora associato al tuo profilo di sicurezza.

## Sostituzione dello Smartphone o Smarrimento

Se stai sostituendo il vecchio smartphone con uno nuovo:
- **Se hai ancora il vecchio telefono funzionante:** Accedi al portale `https://mysignins.microsoft.com/security-info`, approva la notifica sul vecchio telefono, aggiungi il nuovo telefono e solo successivamente rimuovi il vecchio metodo.
- **Se il vecchio smartphone è perso, rubato o rotto:** Non potrai autenticarti autonomamente. È necessario contattare immediatamente il Service Desk IT per farsi emettere un Temporary Access Pass (TAP) valido 8 ore previa identificazione di sicurezza.

## Number Matching e Prevenzione MFA Fatigue
Quando ricevi una notifica push:
- Sullo schermo del computer o dell'app che richiede l'accesso comparirà un numero a due cifre (es. "47").
- Sullo smartphone dovrai digitare esattamente quel numero per autorizzare l'accesso.
- **Attenzione:** Se ricevi una notifica push senza aver richiesto un accesso, seleziona immediatamente **"Non sono io"** e avvisa subito il team di sicurezza all'indirizzo `security@azienda.it`.
