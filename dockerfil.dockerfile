# Utilise une image Python légère
FROM python:3.11-slim

# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers
COPY requirements.txt .
COPY api_analyse.py .

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port
EXPOSE 5000

# Lancer l'API avec Gunicorn (pour Railway)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "api_analyse:app"]
