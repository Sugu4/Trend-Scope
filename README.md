# TrendScope

> Analyse und Vorhersage globaler Social-Media-Trends  
> Python · FastAPI · MongoDB · Elasticsearch · PostgreSQL · scikit-learn

[![Trend](https://img.shields.io/badge/Trend-ansehen-green?style=for-the-badge)](https://sugu4.github.io/Trend-Scope/)  
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)  
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)  
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-blue)](https://fastapi.tiangolo.com)  
[![Docker](https://img.shields.io/badge/Docker-Compose-blue)](https://docker.com)  

---

## Über das Projekt

TrendScope ist ein System zur **Analyse und Vorhersage globaler Social-Media-Trends**. Es sammelt automatisch Daten aus mehreren Quellen, verarbeitet diese mit NLP-Methoden und berechnet Trend-Scores sowie ML-Prognosen — dargestellt in einem interaktiven Dashboard.

**Entwickelt als Schulungsprojekt.**

---

## Schnellstart mit Docker

### Schritt 1 — Docker Desktop installieren

👉 https://www.docker.com/products/docker-desktop/

Windows → Installer herunterladen → installieren → Docker Desktop starten.  
Warten bis das Docker-Symbol in der Taskleiste **grün** wird.

---

### Schritt 2 — Projekt entpacken/ kopieren

Entpacken/ kopieren

---

### Schritt 3 — .env Datei anlegen

`.env.example` kopieren und umbenennen zu `.env`

```bash
cp .env.example .env
```

> Ohne API-Keys läuft alles im **Demo-Modus** mit Beispieldaten.

---

### Schritt 4 — Alles starten

PowerShell im Projektordner öffnen (Shift + Rechtsklick → "PowerShell öffnen"):

```powershell
docker compose up --build
```

Beim **ersten Start** dauert es 5–10 Minuten.  
Bereit wenn du siehst:
```
trendscope-api  | ✅ MongoDB verbunden
trendscope-api  | ✅ Elasticsearch verbunden
trendscope-api  | ✅ PostgreSQL verbunden
trendscope-api  | INFO: Uvicorn running on http://0.0.0.0:8000
```

---

### Schritt 5 — Im Browser öffnen

| Was | URL |
|-----|-----|
| **Frontend Dashboard** | `index.html` direkt im Browser öffnen |
| **API + Swagger Docs** | http://localhost:8000/docs |
| **System-Status** | http://localhost:8000/api/health |

---

### Schritt 6 — Erste Daten sammeln

In Swagger (http://localhost:8000/docs):
1. `POST /api/collect/run` aufklappen
2. **"Try it out"** → **"Execute"**
3. Mehrmals wiederholen für bessere ML-Prognosen

---

## Datenbanken im Browser

### MongoDB → Mongo Express
**URL:** http://localhost:8081 · Login: `admin` / `password`

### Elasticsearch → Kibana
**URL:** http://localhost:5601 · kein Login nötig

### PostgreSQL → pgAdmin
**URL:** http://localhost:5050 · Login: `admin@trendscope.de` / `password`

**pgAdmin einmalig einrichten:**
1. Rechtsklick auf "Servers" → "Register" → "Server..."
2. Tab "General" → Name: `TrendScope`
3. Tab "Connection" → Host: `postgres`, Port: `5432`, User: `postgres`, Passwort: `password`
4. Save

---

## Datenquellen

| Quelle | API-Key | Beschreibung |
|--------|---------|--------------|
| **Reddit** | ❌ Nein | Hot Posts aus 16 Subreddits via RSS |
| **YouTube** | ✅ Ja | Videos zu Trend-Themen via Data API v3 |
| **GitHub Trending** | ❌ Nein | Trending Repositories nach Themen |
| **NewsAPI** | ✅ Optional | Top-Headlines aus 5 Kategorien |

---

## Alle laufenden Dienste

| Container | Port | Beschreibung |
|-----------|------|--------------|
| `trendscope-api` | 8000 | FastAPI Backend |
| `trendscope-mongo` | 27017 | MongoDB |
| `trendscope-mongo-gui` | 8081 | Mongo Express (GUI) |
| `trendscope-es` | 9200 | Elasticsearch |
| `trendscope-kibana` | 5601 | Kibana (GUI) |
| `trendscope-pg` | 5432 | PostgreSQL |
| `trendscope-pgadmin` | 5050 | pgAdmin (GUI) |

---

## Nützliche Befehle

```powershell
docker compose up --build        # Alles starten
docker compose up --build -d     # Im Hintergrund starten
docker compose logs -f           # Logs beobachten
docker compose logs -f backend   # Nur Backend-Logs
docker compose down              # Alles stoppen
docker compose down -v           # Stoppen + Daten löschen
docker compose ps                # Status aller Container
docker compose restart backend   # Nur Backend neu starten
```

---

## API Endpunkte

Alle Endpunkte interaktiv testbar: **http://localhost:8000/docs**

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/health` | Status aller Dienste |
| GET | `/api/trends/` | Top-Trends (neueste) |
| GET | `/api/trends/stats` | Echte Statistiken |
| GET | `/api/trends/?category=tech` | Filter nach Kategorie |
| GET | `/api/trends/search?q=AI` | Keyword-Suche |
| GET | `/api/forecast/` | ML-Prognosen (30 Tage) |
| GET | `/api/forecast/emerging` | Aufsteigende Trends |
| GET | `/api/forecast/declining` | Absinkende Trends |
| POST | `/api/collect/run` | Datensammlung starten |
| GET | `/api/collect/status` | Status letzte Sammlung |

---

## API-Keys einrichten

| Plattform | Wo beantragen | Variable in `.env` |
|-----------|--------------|---------------------|
| YouTube | console.cloud.google.com → YouTube Data API v3 | `YOUTUBE_API_KEY` |
| NewsAPI | newsapi.org/register | `NEWSAPI_KEY` |
| Reddit | reddit.com/prefs/apps | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` |

Nach dem Eintragen:
```powershell
docker compose restart backend
```

---

## Systemarchitektur

```
Reddit RSS + YouTube API + GitHub Trending + NewsAPI
                    ↓
           Data Collector (Python/aiohttp)
                    ↓
           MongoDB (Rohdaten)
                    ↓
           NLP Pipeline (VADER Sentiment)
                    ↓
           Elasticsearch (Analyse/Suche)
                    ↓
           Trend Scoring (scikit-learn)
                    ↓
           PostgreSQL (Ergebnisse + Historie)
                    ↓
           FastAPI Backend (REST API)
                    ↓
           Frontend Dashboard (HTML/JS)
```

---

## Häufige Probleme

| Problem | Lösung |
|---------|--------|
| Docker startet nicht | Docker Desktop öffnen, warten bis Symbol grün |
| Port belegt | `docker compose down` → `up --build` |
| Kibana "not ready" | Normal — ~1 Minute warten, Seite neu laden |
| Elasticsearch mock-mode | `docker compose restart backend` |
| Leere Trends | `POST /api/collect/run` in Swagger ausführen |
| Prognose zeigt +0% | Mehrmals `collect/run` ausführen (min. 5x) |

---

## Lizenz

MIT License — siehe [LICENSE](LICENSE)

Copyright (c) 2026 Süleyman Gümüş
