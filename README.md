# TrendScope 📡 — Backend

> Python · FastAPI · MongoDB · Elasticsearch · PostgreSQL · spaCy · scikit-learn

---

## Projektstruktur

```
trendscope/
├── backend/
│   ├── main.py                  ← FastAPI App + Lifespan
│   ├── api/routes/
│   │   ├── trends.py            ← GET /api/trends
│   │   ├── forecast.py          ← GET /api/forecast
│   │   ├── collect.py           ← POST /api/collect/run
│   │   └── health.py            ← GET /api/health
│   ├── collector/
│   │   └── social.py            ← Reddit · YouTube · Twitter Collector
│   ├── nlp/
│   │   └── pipeline.py          ← spaCy + VADER Sentiment
│   ├── ml/
│   │   └── scoring.py           ← Trend Scoring + scikit-learn Forecast
│   └── db/
│       ├── mongo.py             ← MongoDB (Rohdaten)
│       ├── elastic.py           ← Elasticsearch (Analyse)
│       └── postgres.py          ← PostgreSQL (Ergebnisse / ORM)
├── config/
│   └── settings.py              ← Pydantic Settings (liest .env)
├── .env.example                 ← Vorlage für eigene .env
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── index.html                   ← Frontend (GitHub Pages)
```

---

## Schnellstart (lokal ohne Docker)

### 1. Python-Umgebung

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. spaCy Modelle herunterladen

```bash
python -m spacy download de_core_news_sm
python -m spacy download en_core_web_sm
```

### 3. Konfiguration

```bash
cp .env.example .env
# .env öffnen und API-Keys eintragen (Reddit, YouTube, Twitter)
```

### 4. Datenbanken starten (Docker)

```bash
# Nur die Datenbanken, Backend lokal:
docker compose up -d mongodb elasticsearch postgres
```

### 5. Backend starten

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

→ API läuft auf **http://localhost:8000**  
→ Swagger Docs: **http://localhost:8000/docs**  
→ OpenAPI: **http://localhost:8000/openapi.json**

---

## Alles mit Docker starten

```bash
cp .env.example .env          # API-Keys eintragen
docker compose up --build -d  # Alle Dienste starten
docker compose logs -f        # Logs beobachten
```

---

## API Endpunkte

| Methode | Pfad                    | Beschreibung                          |
|---------|-------------------------|---------------------------------------|
| GET     | `/api/health`           | Status aller Dienste                  |
| GET     | `/api/trends/`          | Top-Trends (sortiert nach Score)      |
| GET     | `/api/trends/search?q=` | Keyword-Suche                         |
| GET     | `/api/forecast/`        | ML-Prognosen für alle Trends          |
| GET     | `/api/forecast/emerging`| Aufsteigende Trends                   |
| GET     | `/api/forecast/declining`| Absinkende Trends                    |
| POST    | `/api/collect/run`      | Datensammlung manuell starten         |
| GET     | `/api/collect/status`   | Status der letzten Sammlung           |

### Beispiel-Anfragen

```bash
# Top 10 Trends
curl http://localhost:8000/api/trends/?limit=10

# Nur Tech-Trends
curl http://localhost:8000/api/trends/?category=tech

# Prognose für 30 Tage
curl http://localhost:8000/api/forecast/?days=30

# Datensammlung starten
curl -X POST http://localhost:8000/api/collect/run?limit=50

# System-Status
curl http://localhost:8000/api/health
```

---

## API-Keys einrichten

### Reddit
1. https://www.reddit.com/prefs/apps → "create another app"
2. Typ: **script**
3. `REDDIT_CLIENT_ID` und `REDDIT_CLIENT_SECRET` in `.env` eintragen

### YouTube
1. https://console.cloud.google.com → APIs & Services → Credentials
2. "YouTube Data API v3" aktivieren
3. API-Key erstellen → `YOUTUBE_API_KEY` in `.env`

### Twitter / X
1. https://developer.twitter.com/en/portal
2. Projekt + App erstellen → **Bearer Token** kopieren
3. `TWITTER_BEARER_TOKEN` in `.env`

> **Ohne API-Keys** läuft das Backend im Mock-Modus — alle Endpunkte liefern Demo-Daten.

---

## Frontend verbinden

Die `index.html` lädt per Standard von `http://localhost:8000/api`. Um das  
Frontend mit dem echten Backend zu verbinden, öffne `index.html` und ändere:

```javascript
// In index.html, Zeile ~20:
const API_BASE = "http://localhost:8000/api";
```

Für GitHub Pages: trage die URL deines deployed Backends ein  
(z. B. Railway: `https://trendscope-xyz.up.railway.app/api`).

---

## Datenfluss

```
Social Media APIs
      ↓
  Collector (aiohttp)          ← Reddit · YouTube · X
      ↓
  MongoDB                      ← Rohdaten (JSON, flexibel)
      ↓
  NLP Pipeline (spaCy/NLTK)   ← Keyword-Extraktion, Sentiment
      ↓
  Elasticsearch                ← Indizierung, Keyword-Aggregation
      ↓
  Trend Scoring (scikit-learn) ← Score-Berechnung, ML-Prognose
      ↓
  PostgreSQL                   ← Strukturierte Ergebnisse
      ↓
  FastAPI                      ← REST API
      ↓
  Frontend (index.html)        ← Dashboard, Charts
```
