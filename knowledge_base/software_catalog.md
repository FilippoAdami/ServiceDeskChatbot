---
id: KB-APP-001
title: Richiesta e Installazione Software Aziendale tramite Company Portal
category: Applicazioni e Software
tags:
  - software
  - company portal
  - intune
  - installazione
  - catalogo
  - licenza
  - approvazione
status: approved
version: 1.0
last_updated: "2026-10-22"
author: IT Workplace Team
summary: Come installare software approvato dal portale aziendale senza privilegi di amministratore e procedura per nuove licenze.
---

# Richiesta e Installazione Software Aziendale tramite Company Portal

Tutti i computer aziendali operano con account utente standard senza diritti di amministratore locale (privilegi elevati) per rispettare i requisiti di sicurezza e prevenire malware. L'installazione di programmi e utility avviene in modalità controllata tramite il portale aziendale.

## Installazione Self-Service tramite Company Portal (Portale Aziendale)

Nel portale aziendale è disponibile un ricco catalogo di applicazioni già testate, pacchettizzate e approvate dalla sicurezza IT:
- Suite Office 365, Microsoft Teams, Zoom, Slack
- Browser web: Google Chrome, Mozilla Firefox, Microsoft Edge
- Strumenti di sviluppo e produttività: VS Code, Git, Notepad++, Adobe Acrobat Reader, 7-Zip, Draw.io

### Come Installare un'Applicazione:
1. Clicca sul menu Start di Windows e cerca **Portale aziendale** (oppure **Company Portal**).
2. Nella scheda **App**, sfoglia le categorie o utilizza la barra di ricerca in alto per individuare l'applicazione desiderata.
3. Clicca sul riquadro dell'applicazione e premi il pulsante **Installa**.
4. L'installazione avviene in background con privilegi elevati gestiti da Microsoft Intune. Non è richiesta alcuna password di amministratore.
5. Al completamento dello scaricamento, lo stato diventerà "Installato" e troverai l'icona nel menu Start.

## Richiesta di Software non a Catalogo o Licenze a Pagamento

Se hai bisogno di un software specializzato a pagamento (ad es. licenza Adobe Creative Cloud, JetBrains All Products, AutoCAD, SPSS) o di un software open-source non presente a catalogo:
1. Accedi al portale Service Desk e apri una richiesta di tipo **"Richiesta Licenza / Nuovo Software"**.
2. Specifica nel modulo:
   - Nome del software e versione desiderata
   - Motivazione aziendale o progetto di riferimento
   - Centro di costo (CdC) del tuo dipartimento per l'eventuale addebito economico
   - Nominativo del Responsabile di Reparto per l'approvazione formale
3. Una volta approvata dal responsabile, il team IT Security effettuerà l'analisi di conformità (licenza, sicurezza e privacy GDPR).
4. Dopo l'approvazione tecnica, la licenza verrà assegnata e il pacchetto comparirà automaticamente nel tuo Company Portal entro 24 ore lavorative.

## Risoluzione Problemi Company Portal

### Errore: "Impossibile completare l'installazione (Codice errore: 0x87D1041C)"
1. Verifica che lo spazio libero su disco C: sia superiore ad almeno 5 GB.
2. Controlla che il dispositivo sia sincronizzato con le policy aziendali: apri **Impostazioni** > **Account** > **Accedi all'azienda o all'istituto di istruzione**, clicca sul tuo account, seleziona **Info** e clicca sul pulsante **Sincronizza**.
3. Riavvia il computer e riprova l'installazione dal Company Portal.
