import pandas as pd
import json
import os
import time
import boto3
import io
import numpy as np

# Imports locaux
from scripts.load_from_s3 import get_latest_s3_file, load_stations_from_s3
from scripts.insert_mongo import migrate_to_mongodb, get_mongo_collection
from scripts.merge_data import transform_wu_data, transform_infoclimat_data

# --- CONFIGURATION S3 ---
S3_BUCKET = os.getenv("S3_BUCKET", "daniel-isaza-airbyte-data-v2").strip()
REGION_NAME = os.getenv("AWS_DEFAULT_REGION", "eu-north-1").strip()

# Récupération sécurisée des clés (vides sur AWS Fargate)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "").strip()
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "").strip()

# Connexion S3 intelligente
if AWS_ACCESS_KEY and AWS_SECRET_KEY:
    # Mode Local (Docker Compose avec .env)
    s3_client = boto3.client(
        "s3", 
        aws_access_key_id=AWS_ACCESS_KEY, 
        aws_secret_access_key=AWS_SECRET_KEY, 
        region_name=REGION_NAME
    )
    print("☁️ Connecté à S3 (Mode Local avec Clés)")
else:
    # Mode Cloud AWS
    s3_client = boto3.client("s3", region_name=REGION_NAME)
    print("☁️ Connecté à S3 (Mode Cloud avec IAM Role)")


def load_airbyte_raw_from_s3(bucket, key):
    """Extraction pure du fichier JSONL depuis S3"""
    if not key: return pd.DataFrame()
    try:
        obj = s3_client.get_object(Bucket=bucket, Key=key)
        df = pd.read_json(io.BytesIO(obj['Body'].read()), lines=True)
        if not df.empty and "_airbyte_data" in df.columns:
            df_norm = pd.json_normalize(df["_airbyte_data"])
            df_norm.columns = df_norm.columns.str.lower().str.strip()
            return df_norm
        df.columns = df.columns.str.lower().str.strip()
        return df
    except Exception as e:
        print(f"⚠️ Erreur lecture S3 ({key}): {e}")
        return pd.DataFrame()

def test_query_performance():
    """Reporting d'accessibilité"""
    print("\n--- 📊 Reporting d'Accessibilité (Performance Query) ---")
    query = {"id_station": "ILAMAD25", "datetime": {"$regex": "^2024-10-05"}}
    start = time.time()
    
    # La collection est récupérée ici dynamiquement
    col = get_mongo_collection()
    if col is None:
        print("⚠️ Statut : Impossible de tester la performance, pas de connexion.")
        return
        
    result = list(col.find(query))
    end = time.time()
    print(f"🔍 Requête : {query}")
    print(f"📄 Résultats : {len(result)} documents trouvés")
    print(f"⏱ Temps d'exécution : {end - start:.4f} secondes")
    if len(result) > 0: print(f"✅ Statut : Performance validée")
    else: print("⚠️ Statut : Aucun document trouvé.")

# --- 1. RÉCUPÉRATION DES CHEMINS ---
prefix_base = "pipeline/airbyte_ingestion"
latest_weather_info_file = get_latest_s3_file(S3_BUCKET, f"{prefix_base}/InfoClimat/")
latest_weather_fr_file = get_latest_s3_file(S3_BUCKET, f"{prefix_base}/Weather_underground_La_Madeleine/")
latest_weather_be_file = get_latest_s3_file(S3_BUCKET, f"{prefix_base}/Weather_underground_Ichtegem/")
latest_stations_file = get_latest_s3_file(S3_BUCKET, "pipeline/stations_meteo/")

print("--- Démarrage du Pipeline d'Unification ---")

# --- 2. RÉFÉRENTIEL DES STATIONS ---
stations_raw = load_stations_from_s3(S3_BUCKET, latest_stations_file) if latest_stations_file else []
enriched_stations = {s["id"]: s for s in stations_raw}
enriched_stations["ILAMAD25"] = {
    "id": "ILAMAD25", "name": "La Madeleine", "city": "La Madeleine",
    "latitude": 50.659, "longitude": 3.07, "elevation": 23,
    "hardware": "other", "software": "EasyWeatherPro_V5.1.6", "license": "Weather Underground Personal License"
}
enriched_stations["IICHTE19"] = {
    "id": "IICHTE19", "name": "WeerstationBS", "city": "Ichtegem",
    "latitude": 51.092, "longitude": 2.999, "elevation": 15,
    "hardware": "other", "software": "EasyWeatherV1.6.6", "license": "Weather Underground Personal License"
}

processed_dfs = []

# --- 3. TRAITEMENT WEATHER UNDERGROUND ---
wu_sources = [(latest_weather_fr_file, "ILAMAD25"), (latest_weather_be_file, "IICHTE19")]
for file_key, s_id in wu_sources:
    df_raw = load_airbyte_raw_from_s3(S3_BUCKET, file_key)
    if not df_raw.empty:
        df_clean = transform_wu_data(df_raw, s_id)
        processed_dfs.append(df_clean)
        print(f"✅ Source WU traitée : {s_id} ({len(df_clean)} lignes)")

# --- 4. EXTRACTION ET TRAITEMENT INFOCLIMAT ---
df_info = load_airbyte_raw_from_s3(S3_BUCKET, latest_weather_info_file)
if not df_info.empty:
    hourly_data_list = []
    for col_name in df_info.columns:
        if col_name.startswith("hourly."):
            s_id = col_name.split(".")[-1]
            for cell_val in df_info[col_name].dropna():
                records = json.loads(cell_val) if isinstance(cell_val, str) else cell_val
                if isinstance(records, list):
                    for record in records:
                        if isinstance(record, dict):
                            new_rec = record.copy()
                            new_rec["id_station"] = s_id
                            hourly_data_list.append(new_rec)
    
    df_info_clean = transform_infoclimat_data(hourly_data_list)
    if not df_info_clean.empty:
        processed_dfs.append(df_info_clean)
        print(f"✅ Source InfoClimat traitée ({len(df_info_clean)} lignes)")

# --- 5. FUSION ET UNIFICATION FINALE ---
if processed_dfs:
    all_data = pd.concat(processed_dfs, ignore_index=True)
    final_weather_data = []
    
    for _, row in all_data.iterrows():
        s_id = row["id_station"]
        station_meta = enriched_stations.get(s_id, {"id": s_id})
        
        w_values = {
            k: (round(float(v), 2) if isinstance(v, (int, float, np.number)) else v) 
            for k, v in row.items() 
            if k not in ["id_station", "datetime", "date", "time"] and pd.notna(v)
        }
        
        final_weather_data.append({
            "id_station": s_id,
            "station_info": station_meta,
            "datetime": str(row.get("datetime", "N/A")),
            "weather_data": w_values
        })

    # --- 6. EXPORT ET MIGRATION ---
    if final_weather_data:
        s3_client.put_object(Body=json.dumps(final_weather_data, indent=4), Bucket=S3_BUCKET, Key="data_transformed/weather_data_unified.json")
        print(f"🚀 Unification terminée : {len(final_weather_data)} enregistrements unifiés et sauvegardés sur S3.")
        
        migrate_to_mongodb(final_weather_data)
        test_query_performance()
else:
    print("⚠️ Aucune donnée n'a pu être collectée. Vérifiez S3.")