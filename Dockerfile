# Utilise une image Python légère
FROM python:3.11-slim

# Définition du répertoire de travail
WORKDIR /app

# Copie uniquement les dépendances en premier pour profiter du cache Docker
COPY requirements.txt .

# Installation des dépendances
RUN pip install --no-cache-dir -r requirements.txt

# 🔄 Nettoyage des anciennes versions éventuelles (important pour éviter les scripts fantômes)
RUN rm -rf /app/scripts /app/main*.py

# Copie du code source actuel
COPY ./scripts /app/scripts
COPY ./main.py /app/

# Exécution du script principal
CMD ["python", "-u", "main.py"]
