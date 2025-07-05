# TestGestionaleME

## Descrizione
Sistema di gestione lavori edilizi sviluppato con Django. Include funzionalità per la gestione di clienti, fornitori e integrazione con strumenti AI per la creazione automatica di ticket.

## Caratteristiche principali
- 🏗️ Gestione completa dei lavori edilizi
- 👥 Gestione clienti e fornitori
- 🤖 Integrazione AI per creazione ticket automatica
- 📧 Sistema di notifiche email
- 📱 Interfaccia responsive
- 🔐 Sistema di autenticazione

## Struttura del progetto
```
├── gestione/                 # App principale Django
│   ├── templates/           # Template HTML
│   ├── static/             # File statici (CSS, JS, immagini)
│   ├── migrations/         # Migrazioni database
│   └── management/         # Comandi personalizzati
├── AITicket/               # Modulo AI per ticket
├── gestione_lavori_edilizi/  # Configurazione Django
└── requirements.txt        # Dipendenze Python
```

## Installazione

### Prerequisiti
- Python 3.8+
- pip

### Setup
1. Clona la repository:
```bash
git clone https://github.com/Thatssteve/TestGestionaleME.git
cd TestGestionaleME
```

2. Installa le dipendenze:
```bash
pip install -r requirements.txt
```

3. Esegui le migrazioni:
```bash
python manage.py migrate
```

4. Crea un superuser (opzionale):
```bash
python manage.py createsuperuser
```

5. Avvia il server di sviluppo:
```bash
python manage.py runserver
```

6. Accedi all'applicazione su `http://localhost:8000`

## Funzionalità

### Gestione Clienti
- Aggiunta, modifica ed eliminazione clienti
- Storico dei lavori per cliente
- Informazioni di contatto complete

### Gestione Fornitori
- Database fornitori con specializzazioni
- Sistema di raccomandazione AI
- Gestione contatti e valutazioni

### Strumenti AI
- Creazione automatica ticket
- Suggerimento fornitori basato su AI
- Analisi automatica delle richieste

### Dashboard
- Panoramica generale dei lavori
- Statistiche e report
- Gestione stato lavori

## Configurazione

### Variabili d'ambiente
Crea un file `.env` nella directory principale:
```
SECRET_KEY=your_secret_key_here
DEBUG=True
DATABASE_URL=sqlite:///db.sqlite3
```

### API Keys
Per utilizzare le funzionalità AI, configura le chiavi API necessarie nel file di configurazione.

## Contribuire
1. Fork del progetto
2. Crea un branch per la tua feature (`git checkout -b feature/AmazingFeature`)
3. Commit delle modifiche (`git commit -m 'Add some AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Apri una Pull Request

## Licenza
Questo progetto è distribuito sotto licenza MIT. Vedi il file `LICENSE` per maggiori dettagli.

## Contatti
- GitHub: [@Thatssteve](https://github.com/Thatssteve)
- Repository: [TestGestionaleME](https://github.com/Thatssteve/TestGestionaleME)

## Screenshots
_Screenshots dell'applicazione verranno aggiunti prossimamente_

---
⭐ Se questo progetto ti è utile, lascia una stella! 