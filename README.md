# Personal Financial Assistant 💰

Benvenuto nel tuo assistente finanziario personale! Questo progetto è un server Flask progettato per essere eseguito su una rete locale (come un Raspberry Pi o un PC Windows) e permette a più utenti di gestire le proprie finanze tramite un'interfaccia web moderna, responsiva e multilingua.

## 🚀 Funzionalità Principali

- **Accesso WiFi Locale**: Grazie a mDNS, puoi accedere al server digitando `http://tumitumi.local:5000` nel browser di qualsiasi dispositivo connesso alla stessa rete.
- **Gestione Multi-utente**: Sistema di registrazione e login sicuro con password criptate.
- **Gestione Transazioni**: Aggiunta rapida di entrate e uscite con supporto per commenti e valute.
- **Categorie Dinamiche & Intelligenti**:
    - Traduzione automatica tramite Google Translate quando aggiungi nuove categorie.
    - Gestione delle traduzioni personalizzate salvate in un file JSON.
    - Eliminazione sicura (solo se non hanno transazioni associate).
- **Dashboard Analitica**: Grafici interattivi (Chart.js) per visualizzare l'andamento di entrate e uscite.
- **Cronologia Avanzata**: Filtri per data, tipo e categoria, con esportazione dei dati in formato CSV.
- **Interfaccia Moderna**: Supporto per modalità Chiara/Scura e multilingua (Italiano, Inglese, Cinese).

---

## 🏗️ Architettura del Codice

Il progetto è strutturato in modo modulare per facilitare le modifiche:

### 1. Backend (Python/Flask)
- **`main.py`**: Il cuore del server. Gestisce le rotte principali, la logica delle categorie, l'integrazione con Google Translate e l'avvio del servizio mDNS.
- **`auth.py`**: Gestisce l'autenticazione (registrazione, login, logout) tramite Flask Blueprints.
- **`database_manager.py`**: Contiene tutte le query SQL. Utilizza SQLite per semplicità e portabilità.
- **`analytics.py`**: Logica per raggruppare i dati delle transazioni e prepararli per i grafici.
- **`translations.py`**: Dizionario statico per le stringhe dell'interfaccia (menu, bottoni, messaggi).
- **`mdns_broadcaster.py`**: Configurazione per rendere il server visibile nella rete locale come `tumitumi.local`.

### 2. Frontend (HTML/CSS/JS)
- **`templates/`**: Contiene i file Jinja2 per le pagine (Dashboard, Finance, History, Stats, More Info).
- **`static/style.css`**: Design responsivo con variabili CSS per il supporto al Dark Mode.
- **`static/script.js`**: Gestisce l'interattività, come i grafici, l'aggiunta di righe nel form e la logica dei popup.

### 3. Dati e Configurazioni
- **`finance_assistant.db`**: Database SQLite (creato automaticamente al primo avvio).
- **`categories.json`**: Elenco globale delle categorie divise per Entrate/Uscite.
- **`categories_translation.py`**: Dizionario delle traduzioni per tutte le categorie (predefinite e personalizzate).

---

## 🛠️ Guida per lo Sviluppatore: Come Modificare il Programma

### Aggiungere una Nuova Pagina
1. Crea un nuovo file `.html` in `templates/` (es. `mia_pagina.html`) estendendo `base.html`.
2. Aggiungi una rotta in `main.py`:
   ```python
   @app.route('/mia_pagina')
   def mia_pagina():
       return render_template('mia_pagina.html')
   ```
3. Aggiungi il link nel menu in `templates/base.html`.

### Modificare le Traduzioni
- Per testi statici (bottoni, etichette): Modifica `translations.py`.
- Per aggiungere una nuova lingua: Aggiungi una nuova chiave (es. `'fr'`) in `translations.py` e aggiorna il selettore di lingua in `base.html` e `main.py`.

### Modificare il Database
Se vuoi aggiungere un campo alle transazioni (es. "Metodo di Pagamento"):
1. Aggiorna la funzione `init_db()` in `database_manager.py`.
2. Aggiorna le funzioni `add_transaction` e `get_paginated_transactions` per gestire il nuovo campo.
3. Aggiorna i form in `index.html` e le tabelle in `history.html`.

### Personalizzare lo Stile
Tutti i colori e i font sono definiti nel blocco `:root` e `[data-theme="dark"]` in `static/style.css`. Modifica queste variabili per cambiare l'aspetto globale del sito in pochi secondi.

---

## 📦 Installazione e Avvio

1. Installa le dipendenze:
   ```bash
   pip install -r requirements.txt
   ```
2. Avvia il server:
   ```bash
   python main.py
   ```
3. Il server si inizializzerà e mostrerà l'indirizzo IP locale. Puoi collegarti da altri dispositivi usando l'IP o `http://tumitumi.local:5000`.

---

## 📝 Note sulla Sicurezza
- Le password sono salvate utilizzando l'hashing di `werkzeug.security`.
- Le query al database utilizzano parametri per prevenire SQL Injection.
- Assicurati che il server sia eseguito in una rete WiFi fidata.
