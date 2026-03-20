# 📡 TrendScope

> Analyse und Vorhersage globaler Social-Media-Trends  
> Python · FastAPI · MongoDB · Elasticsearch · PostgreSQL · spaCy · scikit-learn

---

## 🚀 Schnellstart mit Docker

### Schritt 1 — Docker Desktop installieren

👉 https://www.docker.com/products/docker-desktop/

Windows → Installer herunterladen → installieren → Docker Desktop starten.  
Warten bis das Docker-Symbol in der Taskleiste **grün** wird.

---

### Schritt 2 — Projekt kopieren

Kopiere das Projekt 

---

### Schritt 3 — .env Datei anlegen

`.env.example` kopieren und umbenennen zu `.env`  
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
| 🌐 **Frontend Dashboard** | `index.html` direkt im Browser öffnen |
| ⚡ **API + Swagger Docs** | http://localhost:8000/docs |
| 🟢 **System-Status** | http://localhost:8000/api/health |

---

## 🗄️ Datenbanken im Browser einsehen

### MongoDB → Mongo Express
**URL:** http://localhost:8081 · Login: `admin` / `password`

### Elasticsearch → Kibana  
**URL:** http://localhost:5601 · kein Login nötig

### PostgreSQL → pgAdmin
**URL:** http://localhost:5050 · Login: `admin@trendscope.de` / `password`

**pgAdmin einmalig einrichten:**
1. Rechtsklick auf "Servers" → "Register" → "Server..."
2. Tab "General" → Name: `TrendScope`
3. Tab "Connection":
   - Host: `postgres`
   - Port: `5432`
   - Username: `postgres`
   - Password: `password`
4. Save

Tabellen findest du unter:  
`TrendScope → Databases → trendscope → Schemas → public → Tables`

- **`trend_results`** — Trend-Scores, Rankings, Wachstumsraten
- **`forecast_results`** — ML-Prognosen mit Konfidenzintervallen

---

## 📋 Alle laufenden Dienste

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

## 🔄 Nützliche Befehle

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

## 🌐 API Endpunkte

Alle Endpunkte interaktiv testbar: **http://localhost:8000/docs**

| Methode | Pfad | Beschreibung |
|---------|------|--------------|
| GET | `/api/health` | Status aller Dienste |
| GET | `/api/trends/` | Top-Trends |
| GET | `/api/trends/?category=tech` | Filter nach Kategorie |
| GET | `/api/trends/search?q=AI` | Suche |
| GET | `/api/forecast/` | ML-Prognosen |
| GET | `/api/forecast/emerging` | Aufsteigende Trends |
| GET | `/api/forecast/declining` | Absinkende Trends |
| POST | `/api/collect/run` | Datensammlung starten |

---

## 🔑 API-Keys (optional)

Ohne Keys = Demo-Modus. Für echte Daten in `.env` eintragen:

| Plattform | Wo beantragen | Variable |
|-----------|--------------|----------|
| Reddit | reddit.com/prefs/apps | `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` |
| YouTube | console.cloud.google.com | `YOUTUBE_API_KEY` |
| Twitter/X | developer.twitter.com | `TWITTER_BEARER_TOKEN` |

Nach dem Eintragen: `docker compose restart backend`

---

## ❓ Häufige Probleme

**Docker startet nicht** → Docker Desktop öffnen, warten bis Symbol grün  
**Port belegt** → `docker compose down` dann erneut `up --build`  
**Kibana "not ready"** → Normal, ~1 Minute warten, Seite neu laden  
**pgAdmin leere Tabellen** → Erst Daten sammeln: Swagger → `POST /api/collect/run` → Execute
