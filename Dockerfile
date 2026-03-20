FROM python:3.12-slim

WORKDIR /app

# System-Abhängigkeiten
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ curl \
    && rm -rf /var/lib/apt/lists/*

# Python-Abhängigkeiten
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# spaCy Sprachmodelle
RUN python -m spacy download de_core_news_sm && \
    python -m spacy download en_core_web_sm

# NLTK Daten
RUN python -c "import nltk; nltk.download('vader_lexicon', quiet=True)"

# Anwendungscode
COPY backend/ ./backend/
COPY config/  ./config/

WORKDIR /app/backend

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
