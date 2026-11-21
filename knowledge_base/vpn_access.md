---
id: KB-NET-001
title: Accesso VPN Aziendale e Risoluzione Errori di Connessione
category: Rete e Connettività
tags:
  - vpn
  - smart working
  - telelavoro
  - openvpn
  - anyconnect
  - split tunneling
  - certificato
status: approved
version: 1.3
last_updated: "2026-10-25"
author: IT Network Infrastructure Team
summary: Guida per connettersi alla VPN aziendale da remoto, configurazione client e risoluzione errori frequenti.
---

# Accesso VPN Aziendale e Risoluzione Errori di Connessione

La VPN aziendale (Virtual Private Network) consente ai collaboratori in lavoro agile o trasferta di accedere in sicurezza alle risorse della rete interna (intranet, server file, gestionali legacy, database aziendali).

## Requisiti Preliminari

Per accedere alla VPN aziendale è necessario:
1. Notebook aziendale configurato con sistema operativo aggiornato e antivirus attivo.
2. Connessione internet domestica o hotspot mobile stabile (almeno 5 Mbps in download e upload).
3. Client software **Azienda SecureConnect VPN** preinstallato nella barra delle applicazioni.
4. Token MFA configurato su Microsoft Authenticator.

## Procedura di Connessione

1. Clicca sull'icona dello scudo **Azienda SecureConnect VPN** nell'area di notifica (in basso a destra su Windows, in alto a destra su macOS).
2. Nel campo gateway verifica che sia selezionato l'indirizzo primario: `vpn.azienda.it` (oppure `vpn-backup.azienda.it` in caso di congestione o manutenzione).
3. Clicca su **Connetti**.
4. Quando richiesto, inserisci le tue credenziali di dominio:
   - Username: `nome.cognome` (o `nome.cognome@azienda.it`)
   - Password: la password del tuo account aziendale
5. Approva la notifica push ricevuta sul tuo smartphone tramite l'applicazione Microsoft Authenticator.
6. L'icona del client diventerà verde con l'indicazione **"Connesso - Rete Aziendale Protetta"**.

## Politica di Split Tunneling

La VPN adotta la configurazione di **split tunneling**:
- Il traffico verso le risorse aziendali (indirizzi IP interni `10.0.0.0/8` e `172.16.0.0/12`, domini `*.azienda.local`, file server e intranet) transita attraverso il tunnel cifrato della VPN.
- Il traffico internet generico (navigazione web pubblica, YouTube, streaming, social media) transita direttamente attraverso la tua connessione internet locale per non sovraccaricare la banda della sede centrale.

## Risoluzione Errori Comuni

### Errore: "Credenziali non valide o rifiutate dal server"
1. Assicurati che il tasto Caps Lock (Bloc Maiusc) non sia attivo.
2. Verifica se la password di dominio è scaduta collegandoti a `https://id.azienda.local/reset`.
3. Se hai modificato la password di recente, disconnetti il client VPN, chiudilo completamente dalla barra delle applicazioni e riaprilo.

### Errore: "Timeout di connessione al gateway VPN"
1. Controlla la tua connessione internet aprendo un sito web nel browser.
2. Alcune reti Wi-Fi pubbliche (hotel, treni, aeroporti) o router casalinghi con firewall restrittivo bloccano le porte UDP 443 / 1194. Prova a collegarti momentaneamente tramite hotspot 4G/5G dello smartphone.
3. Se l'hotspot funziona, riavvia il modem/router di casa per liberare eventuali tabelle NAT bloccate.

### Errore: "Certificato di sicurezza scaduto o non attendibile"
Sui notebook aziendali il certificato macchina si rinnova automaticamente ogni 12 mesi. Se il PC è rimasto spento o non connesso per oltre 60 giorni:
- Collega il computer a una rete internet attiva, apri il terminale PowerShell come amministratore ed esegui: `gpupdate /force`.
- Se l'errore persiste, è necessario aprire un ticket al Service Desk per il rinnovo manuale del certificato del dispositivo.
