from fastapi import FastAPI
from pydantic import BaseModel

# 1. On crée l'instance de l'API
app = FastAPI(title="Crypto Bot API")

# 2. On crée la première porte d'entrée : la racine "/"
@app.get("/")
def read_root():
    return {"message": "Bienvenue sur l'API de notre Crypto Bot !"}


# 1. On définit à quoi doit ressembler la commande du client
class MarketData(BaseModel):
    market: str
    open: float
    high: float
    low: float
    close: float
    volume: float



@app.post("/predict")
def get_prediction(data: MarketData):
    # 'data' contient maintenant toutes les infos envoyées par le Dashboard !

    return {
        "statut": "Données reçues avec succès !",
        "market": data.market,
        "decision": "ACHETER",
        "probability": "85%"
    }



# 3. On crée une simulation de la porte "/stats"
@app.get("/stats")
def get_stats(market: str = "BTCUSDT", days: int = 30):
    # 'market' et 'days' ont des valeurs par défaut si le Dashboard ne précise rien.
    # C'est ici que notre script 'analytics.py' (mentionné dans l´ énoncé)
    # ira plus tard calculer les vraies moyennes dans la base de données .
    return {
        "message": "Statistiques calculées avec succès !",
        "market": market,
        "periode_jours": days,
        "prix_moyen_calcule": 61200.5,# Simulation
        "earnings":1000
    } 

