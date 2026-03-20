"""
TrendScope — NLP Pipeline
Verarbeitet rohe Social-Media-Texte:
  1. Tokenisierung & Stopwort-Entfernung
  2. Keyword-Extraktion (spaCy NER + Nomen + Hashtags)
  3. Sentiment-Analyse (VADER + TextBlob)
"""

import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

# ── Lazy Imports (nur laden wenn benötigt) ────────────────────
_nlp_de = None
_nlp_en = None
_sia    = None     # VADER SentimentIntensityAnalyzer


def _load_spacy():
    global _nlp_de, _nlp_en
    if _nlp_de is not None:
        return
    try:
        import spacy
        try:
            _nlp_de = spacy.load("de_core_news_sm")
            logger.info("spaCy Modell 'de_core_news_sm' geladen")
        except OSError:
            logger.warning("spaCy DE-Modell fehlt — führe aus: python -m spacy download de_core_news_sm")
            _nlp_de = None
        try:
            _nlp_en = spacy.load("en_core_web_sm")
            logger.info("spaCy Modell 'en_core_web_sm' geladen")
        except OSError:
            logger.warning("spaCy EN-Modell fehlt — führe aus: python -m spacy download en_core_web_sm")
            _nlp_en = None
    except ImportError:
        logger.warning("spaCy nicht installiert")


def _load_vader():
    global _sia
    if _sia is not None:
        return
    try:
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        import nltk
        try:
            nltk.data.find("sentiment/vader_lexicon.zip")
        except LookupError:
            nltk.download("vader_lexicon", quiet=True)
        _sia = SentimentIntensityAnalyzer()
        logger.info("VADER Sentiment-Analyser geladen")
    except ImportError:
        logger.warning("NLTK nicht installiert")


# ── STOPWÖRTER ────────────────────────────────────────────────

STOPWORDS_DE = {
    "der", "die", "das", "ein", "eine", "und", "in", "von", "mit", "ist",
    "im", "zu", "für", "auf", "an", "bei", "am", "aus", "es", "ich",
    "er", "sie", "wir", "ihr", "sich", "nicht", "auch", "als", "noch",
    "aber", "oder", "wenn", "dann", "dass", "dem", "den", "des", "war",
    "haben", "hat", "wird", "werden", "wie", "was", "mehr", "über",
}

STOPWORDS_EN = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "this", "that", "these",
    "those", "i", "you", "he", "she", "we", "they", "it", "and",
    "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "through", "after",
}

STOPWORDS = STOPWORDS_DE | STOPWORDS_EN


# ── HILFSFUNKTIONEN ───────────────────────────────────────────

def _extract_hashtags(text: str) -> list[str]:
    """Extrahiert Hashtags aus Text."""
    return [tag.lower() for tag in re.findall(r"#(\w+)", text)]


def _clean_text(text: str) -> str:
    """Entfernt URLs, Mentions, Sonderzeichen."""
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"[^\w\s#äöüÄÖÜß]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _simple_keywords(text: str, top_n: int = 10) -> list[str]:
    """
    Fallback-Keyword-Extraktion ohne spaCy:
    Häufige Wörter >= 4 Zeichen, die keine Stopwörter sind.
    """
    words = re.findall(r"\b[a-zA-ZäöüÄÖÜß]{4,}\b", text.lower())
    filtered = [w for w in words if w not in STOPWORDS]
    return [w for w, _ in Counter(filtered).most_common(top_n)]


def _spacy_keywords(text: str, top_n: int = 10) -> list[str]:
    """Keyword-Extraktion über spaCy: Named Entities + Nomen."""
    _load_spacy()
    nlp = _nlp_de or _nlp_en
    if nlp is None:
        return _simple_keywords(text, top_n)

    doc = nlp(text[:10_000])   # spaCy-Limit

    entities = [ent.text.lower() for ent in doc.ents if len(ent.text) >= 3]
    nouns    = [
        token.lemma_.lower()
        for token in doc
        if token.pos_ in ("NOUN", "PROPN")
        and len(token.text) >= 4
        and token.text.lower() not in STOPWORDS
        and not token.is_stop
    ]

    combined = entities + nouns
    return [w for w, _ in Counter(combined).most_common(top_n)]


def get_sentiment(text: str) -> float:
    """
    Gibt einen Sentiment-Score zurück: -1.0 (negativ) bis +1.0 (positiv).
    Nutzt VADER; Fallback: 0.0 (neutral).
    """
    _load_vader()
    if _sia is None:
        return 0.0
    scores = _sia.polarity_scores(text)
    return round(scores["compound"], 3)


# ── HAUPT-PIPELINE ────────────────────────────────────────────

def process_post(post: dict) -> dict:
    """
    Verarbeitet einen einzelnen Post:
    - Bereinigt Text
    - Extrahiert Keywords (spaCy + Hashtags)
    - Berechnet Sentiment
    Gibt den Post-Dict mit befüllten Feldern zurück.
    """
    text = post.get("text", "")
    clean = _clean_text(text)

    hashtags = _extract_hashtags(text)
    keywords = _spacy_keywords(clean, top_n=8)

    # Hashtags zu Keywords hinzufügen (unique)
    all_keywords = list(dict.fromkeys(keywords + hashtags))[:15]

    sentiment = get_sentiment(clean)

    return {
        **post,
        "text_clean": clean,
        "keywords": all_keywords,
        "sentiment": sentiment,
    }


def process_posts(posts: list[dict]) -> list[dict]:
    """Verarbeitet eine Liste von Posts."""
    processed = []
    for post in posts:
        try:
            processed.append(process_post(post))
        except Exception as e:
            logger.error("NLP-Fehler für Post %s: %s", post.get("external_id", "?"), e)
    return processed


def aggregate_keywords(posts: list[dict], top_n: int = 20) -> list[dict]:
    """
    Zählt Keyword-Häufigkeiten über alle Posts.
    Gibt Liste von {keyword, count, avg_sentiment} zurück.
    """
    keyword_counts: Counter = Counter()
    keyword_sentiment: dict[str, list[float]] = {}

    for post in posts:
        sentiment = post.get("sentiment", 0.0)
        for kw in post.get("keywords", []):
            keyword_counts[kw] += 1
            keyword_sentiment.setdefault(kw, []).append(sentiment)

    results = []
    for kw, count in keyword_counts.most_common(top_n):
        sentiments = keyword_sentiment.get(kw, [0.0])
        avg_sent = round(sum(sentiments) / len(sentiments), 3)
        results.append({
            "keyword": kw,
            "count": count,
            "avg_sentiment": avg_sent,
        })

    return results
