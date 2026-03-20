"""
TrendScope — NLP Pipeline
Keyword-Extraktion und Sentiment-Analyse ohne spaCy-Abhängigkeit.
"""

import re
import logging
from collections import Counter

logger = logging.getLogger(__name__)

_sia = None


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
    except Exception as e:
        logger.warning("VADER nicht verfügbar: %s", e)


# ── Erweiterte Stopwörter ─────────────────────────────────────

STOPWORDS = {
    # Deutsch
    "der", "die", "das", "ein", "eine", "und", "in", "von", "mit", "ist",
    "im", "zu", "für", "auf", "an", "bei", "am", "aus", "es", "ich",
    "er", "sie", "wir", "ihr", "sich", "nicht", "auch", "als", "noch",
    "aber", "oder", "wenn", "dann", "dass", "dem", "den", "des", "war",
    "haben", "hat", "wird", "werden", "wie", "was", "mehr", "über",
    # Englisch
    "the", "a", "an", "is", "are", "was", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "this", "that", "these",
    "those", "i", "you", "he", "she", "we", "they", "it", "and",
    "or", "but", "in", "on", "at", "to", "for", "of", "with",
    "by", "from", "up", "about", "into", "through", "after",
    # YouTube-spezifische Stopwörter
    "video", "videos", "watch", "subscribe", "like", "comment",
    "channel", "youtube", "shorts", "short", "new", "best", "top",
    "make", "get", "know", "want", "need", "just", "time", "good",
    "also", "back", "after", "use", "two", "how", "our", "work",
    "first", "well", "way", "even", "here", "because", "come",
    "could", "now", "look", "think", "see", "been", "its", "than",
    "then", "can", "only", "over", "such", "your", "my", "no",
    "made", "before", "right", "too", "any", "same", "tell",
    "boy", "old", "follow", "show", "going", "help", "take",
    "give", "live", "still", "big", "down", "much", "say",
    "every", "found", "never", "set", "put", "end", "does",
    "another", "well", "large", "often", "hand", "high", "place",
    "hold", "today", "during", "hundred", "real", "call", "feel",
    "keep", "let", "why", "part", "try", "turn", "move", "face",
    "doing", "tell", "asked", "went", "man", "read", "need", "land",
    # Zu generische Wörter
    "space", "open", "says", "said", "thread", "using", "used",
    "code", "repo", "library", "tool", "build", "built", "list",
    "report", "based", "support", "project", "release", "update",
    "version", "issue", "feature", "free", "source", "latest",
    "week", "month", "year", "people", "world", "company", "have",
    "please", "everyone", "engineer", "research", "everyone", "anyone",
    "someone", "something", "nothing", "everything", "anything", "really",
    "actually", "probably", "already", "always", "never", "maybe", "still",
    "pretty", "quite", "rather", "almost", "enough", "around", "against",
    "without", "within", "between", "through", "during", "while", "where",
    "since", "until", "unless", "although", "however", "therefore", "because",
    "despite", "whether", "either", "neither", "both", "each", "every",
    "share", "post", "link", "comment", "read", "write", "click", "check",
    "find", "know", "think", "feel", "want", "need", "seem", "become",
    "will", "more", "with", "they", "been", "were", "when", "which",
    "their", "there", "what", "about", "would", "other", "some",
    "than", "into", "each", "take", "come", "look", "only", "over",
    "think", "most", "both", "many", "mean", "note", "last", "long",
    "great", "little", "form", "place", "line", "life", "work",
}

# ── Wichtige Themen-Keywords die immer behalten werden ────────
IMPORTANT_KEYWORDS = {
    "ai", "artificial", "intelligence", "climate", "change", "crypto",
    "bitcoin", "blockchain", "politics", "election", "trump", "biden",
    "technology", "innovation", "science", "nasa", "economy",
    "inflation", "cybersecurity", "hacking", "ukraine", "russia", "china",
    "covid", "health", "cancer", "nuclear", "war", "peace", "energy",
    "renewable", "solar", "electric", "tesla", "openai", "chatgpt",
    "google", "microsoft", "apple", "amazon", "meta", "twitter",
    "stock", "market", "dollar", "euro", "oil", "gas", "food",
    "water", "environment", "pollution", "global", "warming",
    "quantum", "robot", "autonomous", "machine", "learning", "data",
    "privacy", "security", "hack", "breach", "virus", "vaccine",
    "iran", "israel", "gaza", "nato", "military", "government",
    "president", "minister", "congress", "parliament", "law", "court",
}


def _clean_text(text: str) -> str:
    text = re.sub(r"http\S+|www\.\S+", "", text)
    text = re.sub(r"@\w+", "", text)
    text = re.sub(r"[^\w\s#äöüÄÖÜß]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _extract_hashtags(text: str) -> list[str]:
    return [tag.lower() for tag in re.findall(r"#(\w+)", text)
            if len(tag) >= 3 and tag.lower() not in STOPWORDS]


def _extract_keywords(text: str, top_n: int = 10) -> list[str]:
    """Verbesserte Keyword-Extraktion ohne spaCy."""
    words = re.findall(r"\b[a-zA-ZäöüÄÖÜß]{4,}\b", text.lower())

    scored = []
    for word in words:
        if word in STOPWORDS:
            continue
        score = 1
        if word in IMPORTANT_KEYWORDS:
            score = 3  # Wichtige Keywords bevorzugen
        if len(word) >= 7:
            score += 1  # Längere Wörter sind spezifischer
        scored.append((word, score))

    # Aggregieren
    keyword_scores: dict[str, int] = {}
    for word, score in scored:
        keyword_scores[word] = keyword_scores.get(word, 0) + score

    sorted_keywords = sorted(keyword_scores.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_keywords[:top_n]]


def get_sentiment(text: str) -> float:
    _load_vader()
    if _sia is None:
        return 0.0
    try:
        scores = _sia.polarity_scores(text)
        return round(scores["compound"], 3)
    except Exception:
        return 0.0


def process_post(post: dict) -> dict:
    text = post.get("text", "")
    clean = _clean_text(text)
    hashtags = _extract_hashtags(text)
    keywords = _extract_keywords(clean, top_n=8)
    all_keywords = list(dict.fromkeys(keywords + hashtags))[:15]
    sentiment = get_sentiment(clean)
    return {**post, "text_clean": clean, "keywords": all_keywords, "sentiment": sentiment}


def process_posts(posts: list[dict]) -> list[dict]:
    processed = []
    for post in posts:
        try:
            processed.append(process_post(post))
        except Exception as e:
            logger.error("NLP-Fehler: %s", e)
    return processed


def aggregate_keywords(posts: list[dict], top_n: int = 20) -> list[dict]:
    keyword_counts: Counter = Counter()
    keyword_sentiment: dict[str, list[float]] = {}

    for post in posts:
        sentiment = post.get("sentiment", 0.0)
        for kw in post.get("keywords", []):
            if len(kw) < 3 or kw in STOPWORDS:
                continue
            keyword_counts[kw] += 1
            keyword_sentiment.setdefault(kw, []).append(sentiment)

    results = []
    for kw, count in keyword_counts.most_common(top_n):
        sentiments = keyword_sentiment.get(kw, [0.0])
        avg_sent = round(sum(sentiments) / len(sentiments), 3)
        results.append({"keyword": kw, "count": count, "avg_sentiment": avg_sent})

    return results
# Append to STOPWORDS
STOPWORDS.update({
    "best", "time", "world", "global", "people", "year", "years",
    "life", "news", "week", "days", "long", "little", "very",
    "great", "many", "most", "some", "they", "them", "their",
    "what", "when", "where", "which", "while", "with", "would",
    "about", "after", "again", "against", "between", "both",
    "each", "further", "into", "more", "other", "same", "than",
    "then", "there", "these", "they", "this", "those", "through",
    "under", "until", "very", "well", "were", "what", "when",
    "where", "which", "while", "will", "with", "would", "your",
})
