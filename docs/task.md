 ![🧪](https://fonts.gstatic.com/s/e/notoemoji/17.0/1f9ea/32.png) **Prova Tecnica: Analisi dei requisiti e progettazione di un bot di supporto IT (Service Desk)**

***Contesto***

Un’azienda di medie dimensioni (circa 500 dipendenti) gestisce il supporto IT interno tramite un service desk tradizionale.  
Il volume di richieste è elevato e riguarda soprattutto problemi ricorrenti, come:

- reset password
- problemi di accesso alla posta elettronica
- malfunzionamenti software comuni
- richieste di assistenza generiche

L’azienda sta valutando l’introduzione di un **bot di supporto IT** integrato con la chat aziendale e con il sistema di ticketing, con l’obiettivo di migliorare l’efficienza del servizio e ridurre il carico operativo sul team IT.

L’obiettivo della prova è valutare la capacità del candidato di:

- analizzare un **problema reale di business**;
- raccogliere e strutturare **requisiti funzionali e non funzionali**;
- tradurre i requisiti in una **proposta tecnica coerente**;
- sviluppare un **prototipo funzionante**, anche semplice;
- comunicare in modo chiaro scelte, assunzioni e limiti.

![✍️](https://fonts.gstatic.com/s/e/notoemoji/17.0/270d_fe0f/32.png) **Cosa ci aspettiamo**

***1. Raccolta e definizione dei requisiti***

Viene richiesto di individuare, descrivere e motivare :

- **Requisiti funzionali (esempi)**

- che tipo di richieste deve gestire il bot;

- quando il bot può risolvere autonomamente un problema;

- quando e come deve aprire un ticket;

- quali informazioni deve raccogliere dall’utente.

- **Requisiti non funzionali (esempi)**

- usabilità e semplicità di utilizzo;

- affidabilità e gestione degli errori;

- tracciabilità delle conversazioni;

- estendibilità futura del sistema.

***2. Progettazione dell’architettura***

Viene richiesto:

- Una **descrizione dell’architettura logica** del sistema (anche ad alto livello).

- I **componenti principali** (es. interfaccia utente, backend, logica del bot, integrazione ticketing).

- Il **flusso di una richiesta utente**, ad esempio:

- “Non riesco ad accedere alla mail”

- Una breve analisi riguardo a:

- come viene gestito l’input testuale dell’utente;

- come il bot riconosce il tipo di richiesta (anche con approccio rule-based);

- come e quando viene aperto un ticket;

- come vengono gestiti logging ed errori.

***3. Prototipo di implementazione***

Viene richiesto lo sviluppo di un semplice prototipo dimostrativo in grado di:

- accettare un input testuale da parte dell’utente;

- riconoscere almeno 3 tipologie di richieste, ad esempio:

- reset password;

- problemi email;

- richiesta generica di supporto;

- restituire una risposta coerente;

- simulare l’apertura di un ticket (mock o output testuale).

- Tecnologie: linguaggio e framework a scelta del candidato  
  (es. Python + Flask/FastAPI, Node.js + Express, ecc.).

***Non è richiesto l’uso di AI avanzata o modelli LLM: una soluzione rule-based è perfettamente accettabile.***


