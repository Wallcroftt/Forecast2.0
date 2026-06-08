import os
from pymongo import MongoClient, ASCENDING, DESCENDING

# Connexion dynamique à MongoDB
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")

def get_mongo_collection():
    """Initialise la connexion à MongoDB et renvoie la collection"""
    try:
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = client["weather_database"]
        col = db["weather_data"]
        
        # Création des index (sécurisé)
        col.create_index([("id_station", ASCENDING), ("datetime", DESCENDING)])
        print(f"✅ Connecté à MongoDB sur : {MONGO_URI}")
        return col
    except Exception as e:
        print(f"❌ Erreur connexion MongoDB : {e}")
        return None

def clean_and_audit_data(data):
    """
    Nettoie les données (prise en charge des champs non recevables) 
    et calcule les métriques d'audit et le pourcentage d'erreur.
    """
    print("\n--- Audit Final de Qualité et Nettoyage ---")
    print("🔍 Contrôle des champs non recevables : Analyse du typage des variables numériques...")
    
    total = len(data)
    if total == 0:
        return data
        
    metrics = {
        "temperature": 0, "pressure": 0, "humidity": 0, 
        "dew_point": 0, "wind_speed": 0, "wind_gust": 0, "precipitations": 0
    }
    
    # Variables pour le calcul des champs invalides
    numeric_fields_to_check = ["temperature", "pressure", "humidity", "dew_point", "wind_speed", "wind_gust", "precip_rate", "precip_1h", "precip_accum", "elevation"]
    total_fields_checked = 0
    invalid_fields_count = 0

    cleaned_data = []

    for row in data:
        wd = row.get("weather_data", {})
        
        # 1. Prise en charge des champs non recevables
        for key in numeric_fields_to_check:
            if key in wd and wd[key] is not None:
                val = wd[key]
                total_fields_checked += 1
                
                # Si la valeur est une string au lieu d'un nombre
                if isinstance(val, str):
                    try:
                        wd[key] = float(val)
                    except ValueError:
                        invalid_fields_count += 1
                        wd[key] = None  
                elif not isinstance(val, (int, float)):
                    invalid_fields_count += 1
                    wd[key] = None

        # 2. Calcul de la complétude
        if wd.get("temperature") is not None: metrics["temperature"] += 1
        if wd.get("pressure") is not None: metrics["pressure"] += 1
        if wd.get("humidity") is not None: metrics["humidity"] += 1
        if wd.get("dew_point") is not None: metrics["dew_point"] += 1
        if wd.get("wind_speed") is not None: metrics["wind_speed"] += 1
        if wd.get("wind_gust") is not None: metrics["wind_gust"] += 1
        if wd.get("precip_rate") is not None or wd.get("precip_1h") is not None or wd.get("precip_accum") is not None:
            metrics["precipitations"] += 1

        row["weather_data"] = wd
        cleaned_data.append(row)

    # --- Calcul des résultats finaux ---
    completeness = [
        metrics["temperature"], metrics["pressure"], metrics["humidity"],
        metrics["dew_point"], metrics["wind_speed"], metrics["wind_gust"], metrics["precipitations"]
    ]
    avg_score = (sum(completeness) / (7 * total)) * 100

    # Calcul du pourcentage d'erreur
    error_rate = (invalid_fields_count / total_fields_checked * 100) if total_fields_checked > 0 else 0

    print(f"✅ Validation du typage terminée. Champs numériques vérifiés : {total_fields_checked}")
    print(f"⚠️ Chaînes de caractères ou formats non recevables interceptés : {invalid_fields_count}")
    print(f"📉 Taux d'erreur (données aberrantes) : {error_rate:.2f}%")
    print(f"📈 Score de Viabilité Opérationnelle (Complétude) : {avg_score:.2f}%")

    return cleaned_data

def migrate_to_mongodb(data):
    """Insère les données unifiées et nettoyées dans MongoDB"""
    if not data:
        print("⚠️ Aucune donnée à insérer dans MongoDB.")
        return
    
    col = get_mongo_collection()
    if col is None:
        return
        
    try:
        cleaned_data = clean_and_audit_data(data)
        
        col.delete_many({})
        col.insert_many(cleaned_data)
        print(f"🚀 Migration réussie : {len(cleaned_data)} documents insérés.")
    except Exception as e:
        print(f"❌ Erreur lors de l'insertion MongoDB : {e}")