from pymongo import MongoClient
from pymongo.errors import ConnectionFailure

client = MongoClient("mongodb://localhost:27017/", serverSelectionTimeoutMS=2000)

# Verbindung (mit Error-Check beim Import)
try:
    client.admin.command('ping')  # Testet echte Verbindung
    db = client["trend_scope"]
    posts_collection = db["posts"]
    print("MongoDB verbunden!")
except ConnectionFailure:
    print("MongoDB nicht erreichbar - starte MongoDB!")
    raise
