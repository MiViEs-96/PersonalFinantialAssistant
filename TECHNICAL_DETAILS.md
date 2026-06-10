# Documentazione Tecnica Dettagliata 🛠️

Questa documentazione fornisce una spiegazione approfondita di ogni script e della logica interna del sistema.

---

## 1. `main.py` - Il Controller Principale
Questo è il file principale che avvia il server Flask e coordina tutti i moduli.

### Funzioni Chiave:
- **`inject_translations()`**: Un `context_processor` che rende disponibile la funzione `_()` in tutti i template HTML. Cerca le traduzioni prima in `categories_translation.json` e poi in `translations.py`.
- **`index()`**: Gestisce la pagina di gestione finanziaria. Calcola il saldo del mese corrente e del mese precedente, e prepara i dati per la visualizzazione delle ultime 5 transazioni.
- **`add_transaction()`**: Riceve i dati dal form (supporta più righe contemporaneamente) e li inserisce nel database tramite `database_manager`.
- **`translate_category_api()`**: Endpoint POST che utilizza la libreria `googletrans`. Prende un nome e una lingua di origine e restituisce le traduzioni in IT, EN e ZH.
- **`add_category()`**: Salva una nuova categoria in `categories.json` (usando il nome inglese come chiave) e memorizza le traduzioni fornite dall'utente in `categories_translation.json`.
- **`more_info()`**: Prepara i dati per la pagina di amministrazione, inclusa la lista utenti e il conteggio dell'utilizzo globale di ogni categoria.
- **`delete_category()`**: Verifica che una categoria non sia usata in nessuna transazione prima di eliminarla dai file JSON/Python.

---

## 2. `auth.py` - Gestione Identità
Gestisce la sicurezza degli accessi tramite un Blueprint di Flask.

- **`register()`**: Prende Nome, Nickname e Password. Cripta la password usando `generate_password_hash` prima di salvarla.
- **`login()`**: Permette l'accesso usando sia il Nickname che il Nome Completo. Se le credenziali sono corrette, salva l'ID utente e il Nickname nella sessione Flask.
- **`logout()`**: Pulisce la sessione, disconnettendo l'utente.

---

## 3. `database_manager.py` - Interfaccia SQLite
Questo script isola tutta la logica SQL.

### Schema Tabelle:
- **`users`**: `id`, `full_name`, `nickname`, `password` (hash), `last_access`.
- **`transactions`**: `id`, `date`, `amount`, `currency`, `direction` (entrata/uscita), `category` (chiave inglese), `nickname` (FK), `comment`.

### Funzioni Importanti:
- **`init_db()`**: Crea le tabelle se non esistono.
- **`update_user_profile()`**: Aggiorna i dati dell'utente. Se il nickname cambia, esegue una query `UPDATE` sulla tabella `transactions` per mantenere l'integrità dei dati (cascading manuale).
- **`get_paginated_transactions()`**: Gestisce la logica di filtraggio e paginazione per la pagina "History".
- **`get_category_usage_counts()`**: Esegue una `GROUP BY` per contare quante transazioni esistono per ogni categoria a livello globale.

---

## 4. `analytics.py` - Elaborazione Dati
Modulo puro per la logica di calcolo dei grafici.

- **`process_data_for_charts(transactions)`**: Prende una lista di transazioni e restituisce un dizionario formattato per **Chart.js**. Divide le somme per categoria e calcola i totali per il grafico a torta.

---

## 5. `translations.py` - Dizionario Interfaccia
Contiene le stringhe statiche del sito. È organizzato come un dizionario nidificato: `TRANSLATIONS[lingua][chiave]`.
*Nota: Se aggiungi un nuovo elemento nell'interfaccia, devi aggiungere la relativa traduzione qui per tutte le lingue.*

---

## 6. `mdns_broadcaster.py` - Visibilità di Rete
Permette al server di essere "trovato" senza conoscere l'indirizzo IP.

- **`get_ip_address()`**: Identifica l'IP locale della macchina (es. `192.168.1.15`).
- **`start_mdns_broadcast()`**: Registra il nome `tumitumi.local` sulla rete locale. Utilizza la libreria `zeroconf`.

---

## 7. `static/script.js` - Logica Frontend
Il cuore dell'interattività dell'utente.

- **`autoTranslate()`**: Chiamata quando l'utente finisce di scrivere il nome di una nuova categoria. Interroga il server e riempie i campi grigi.
- **`submitCategory()`**: Raccoglie i dati del popup, assicura che ci sia un nome inglese per il database e invia tutto al server.
- **`addRow()`**: Clona dinamicamente le righe del form di inserimento transazioni.
- **`toggleTheme()`**: Salva la preferenza del tema (Light/Dark) nel `localStorage` del browser.

---

## 8. Flusso dei Dati: Aggiunta Categoria
1. L'utente clicca su "Altro...".
2. Il JS apre il popup e imposta la lingua primaria.
3. L'utente scrive "Mela" -> `autoTranslate()` riempie "Apple" e "苹果".
4. Al "Salva", il JS invia "Apple" come nome principale e l'oggetto con le 3 traduzioni.
5. Il server salva "Apple" in `categories.json`.
6. Il server salva le traduzioni in `categories_translation.json`.
7. Da quel momento, `inject_translations` userà quel file per mostrare "Mela" se il sito è in italiano.
