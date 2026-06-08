import pandas as pd
import numpy as np
import re

# --- FONCTIONS DE CONVERSION MATHÉMATIQUES ---
def fahrenheit_to_celsius(f):
    return (f - 32) * 5.0/9.0

def inHg_to_hPa(inhg):
    return inhg * 33.8639

def mph_to_kmh(mph):
    return mph * 1.60934

def in_to_mm(inches):
    return inches * 25.4

def add_datetime(df):
    """Génère une colonne datetime factice basée sur l'index pour les fichiers Excel WU"""
    base_date = pd.Timestamp("2024-10-01 00:00:00")
    # Ajoute 5 minutes par ligne
    df["datetime"] = [base_date + pd.Timedelta(minutes=5*i) for i in range(len(df))]
    return df

# --- FONCTION DE NETTOYAGE ---
def clean_numeric_string(s):
    """Nettoyage des caractères spéciaux et unités (ex: '84\u00a0%' -> 84.0)"""
    if pd.isna(s) or s == "": return np.nan
    cleaned = re.sub(r'[^0-9.\-]', '', str(s).replace(',', '.'))
    try:
        return float(cleaned)
    except:
        return np.nan

# --- LOGIQUES DE TRANSFORMATION PAR SOURCE ---

def transform_wu_data(df, station_id):
    """Applique le nettoyage, les conversions et le renommage pour Weather Underground"""
    df = add_datetime(df)
    df["id_station"] = station_id
    
    WU_MAP = {
        "dew point": "dew_point", "speed": "wind_speed", "wind": "wind_direction", 
        "precip. rate.": "precip_rate", "precip. accum.": "precip_accum", "gust": "wind_gust"
    }
    
    conversions_to_apply = [
        ("temperature", fahrenheit_to_celsius),
        ("dew point", fahrenheit_to_celsius),
        ("pressure", inHg_to_hPa),
        ("gust", mph_to_kmh),
        ("speed", mph_to_kmh),
        ("precip. rate.", in_to_mm),
        ("precip. accum.", in_to_mm),
        ("humidity", lambda x: x),
        ("solar", lambda x: x),
        ("uv", lambda x: x)
    ]
    
    for col_name, func in conversions_to_apply:
        if col_name in df.columns:
            df[col_name] = df[col_name].apply(clean_numeric_string)
            df[col_name] = func(df[col_name]).round(2)
            
    df.rename(columns=WU_MAP, inplace=True)
    return df

def transform_infoclimat_data(hourly_data_list):
    """Transforme la liste brute InfoClimat en un DataFrame propre et typé"""
    if not hourly_data_list:
        return pd.DataFrame()
        
    infoclimat = pd.DataFrame(hourly_data_list)
    
    INFO_MAP = {
        "dh_utc": "datetime", "pression": "pressure", "vent_rafales": "wind_gust", 
        "point_de_rosee": "dew_point", "humidite": "humidity", "vent_moyen": "wind_speed", 
        "vent_direction": "wind_direction", "visibilite": "visibility", "pluie_1h": "precip_1h"
    }
    infoclimat.rename(columns=INFO_MAP, inplace=True)
    
    # Typage numérique pour garantir l'intégration MongoDB
    cols_to_numeric = ["temperature", "pressure", "humidity", "dew_point", "wind_speed", "wind_gust", "precip_1h"]
    for c in cols_to_numeric:
        if c in infoclimat.columns:
            infoclimat[c] = pd.to_numeric(infoclimat[c], errors='coerce')
            
    return infoclimat