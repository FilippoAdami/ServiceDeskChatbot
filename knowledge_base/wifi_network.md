---
id: KB-NET-002
title: Connessione alla Rete Wi-Fi Aziendale e Risoluzione Problemi Connettività
category: Rete e Connettività
tags:
  - wifi
  - wireless
  - ssid
  - 802.1x
  - certificato
  - dhcp
  - dns
status: approved
version: 1.0
last_updated: "2026-10-18"
author: IT Network Infrastructure Team
summary: Istruzioni per collegarsi alla rete Wi-Fi aziendale Corporate e Guest, diagnostica segnale e IP.
---

# Connessione alla Rete Wi-Fi Aziendale e Risoluzione Problemi Connettività

In tutte le sedi e filiali aziendali sono irradiate reti wireless gestite centralmente. Questa guida illustra come connettere i dispositivi aziendali e ospiti e come diagnosticare eventuali anomalie di segnale o indirizzamento.

## Reti Wireless Disponibili

All'interno degli uffici sono visibili le seguenti reti wireless (SSID):
- **Azienda-Corporate:** Rete protetta ad alte prestazioni riservata esclusivamente ai notebook e dispositivi gestiti dall'azienda. Autenticazione tramite protocollo WPA3-Enterprise / 802.1X con certificato del dispositivo.
- **Azienda-Guest:** Rete isolata dedicata a consulenti, clienti e smartphone personali. Accesso tramite captive portal con codice OTP inviato via SMS.

## Connessione alla Rete Azienda-Corporate

I PC aziendali (Windows e macOS) sono preconfigurati per connettersi in automatico alla rete `Azienda-Corporate`:
1. Clicca sull'icona delle reti Wi-Fi nella barra delle applicazioni.
2. Seleziona **Azienda-Corporate** e verifica che sia spuntata la casella "Connetti automaticamente".
3. Clicca su **Connetti**.
4. Se il sistema richiede le credenziali, inserisci:
   - Identità: `nome.cognome@azienda.it`
   - Password: password del proprio account aziendale
5. Accetta il certificato del server RADIUS (emesso da `CA-Azienda-Internal`) se richiesto al primo collegamento.
6. La connessione assegna un indirizzo IP dinamico nella subnet dell'ufficio locale via DHCP.

## Connessione alla Rete Azienda-Guest

Per fornitori, visitatori o smartphone personali:
1. Seleziona la rete Wi-Fi **Azienda-Guest**.
2. Il browser aprirà automaticamente la pagina del Captive Portal (`https://guest.azienda.it`). Se non si apre, digita `1.1.1.1` nella barra degli indirizzi.
3. Inserisci nome, cognome, numero di cellulare e il nome del referente interno dell'incontro.
4. Digita il codice PIN a 4 cifre ricevuto via SMS sul tuo smartphone.
5. La sessione ospite è valida per 8 ore continue con navigazione web standard (porte 80 e 443).

## Risoluzione Problemi di Connettività Wi-Fi

### Segnale debole o disconnessioni frequenti
- Assicurati di non trovarti in zone schermate (ascensori, locali tecnici, seminterrati).
- Spegni e riaccendi la scheda Wi-Fi del computer tramite l'apposito interruttore o dalle impostazioni di sistema.
- Se ti trovi in una sala riunioni affollata, il punto di accesso potrebbe essere saturo; prova a spostarti o a utilizzare una presa di rete cablata Ethernet a parete.

### "Nessuna connessione a Internet, protetta" o Indirizzo IP 169.254.x.x
Se la scheda Wi-Fi ottiene un indirizzo APIPA (169.254.x.x), il server DHCP aziendale non ha risposto:
1. Apri il prompt dei comandi (cmd) o PowerShell.
2. Esegui i seguenti comandi in sequenza:
   ```cmd
   ipconfig /release
   ipconfig /renew
   ipconfig /flushdns
   ```
3. Se l'indirizzo IP non viene rilasciato, disattiva e riattiva la scheda di rete wireless da "Connessioni di rete".
4. Se il problema persiste anche per altri colleghi nella stessa stanza, potrebbe essere in corso un disservizio dello switch locale o del controller Wi-Fi (apri una segnalazione di guasto rete).
