import os
import requests
from flask import Flask, request, jsonify
from mistralai import Mistral

app = Flask(__name__)

# Initialisation du client Mistral AI
# La variable MISTRAL_API_KEY doit être configurée sur Railway
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
ANALYSIS_API_KEY = os.getenv("ANALYSIS_API_KEY")

if not MISTRAL_API_KEY:
    print("⚠️ ATTENTION : La variable MISTRAL_API_KEY n'est pas configurée !")

@app.route('/analyse', methods=['POST'])
def analyse_submission():
    # 1. Vérification de la sécurité (Clé API partagée entre le Bot et l'API)
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header != f"Bearer {ANALYSIS_API_KEY}":
        return jsonify({"status": "error", "message": "Accès non autorisé"}), 401

    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Aucune donnée reçue"}), 400

    file_url = data.get("file_url")
    file_type = data.get("file_type", "code")  # 'code' ou 'image'

    if not file_url:
        return jsonify({"status": "error", "message": "URL du fichier manquante"}), 400

    try:
        # Initialisation du client Mistral
        client = Mistral(api_key=MISTRAL_API_KEY)

        # --- CAS 1 : ANALYSE D'UNE IMAGE ---
        if file_type == "image":
            prompt = """
            Tu es un inspecteur et designer critique pour un jeu de simulation d'entreprise sur Discord.
            Analyse cette image qui est une soumission de travail d'un joueur (graphisme, interface, modèle 3D ou preuve de travail).
            Évalue la qualité visuelle, l'effort fourni et la pertinence.
            Tu dois obligatoirement répondre UNIQUEMENT par un nombre entier entre 10 et 100 représentant ta note.
            Aucun texte explicatif, aucun commentaire, juste le nombre.
            """

            response = client.chat.complete(
                model="pixtral-12b-latest",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": file_url}
                        ]
                    }
                ]
            )

        # --- CAS 2 : ANALYSE DE CODE / TEXTE ---
        else:
            # Téléchargement du contenu du fichier texte/code depuis Supabase
            download_res = requests.get(file_url, timeout=10)
            if download_res.status_code != 200:
                return jsonify({"status": "error", "message": "Impossible de télécharger le fichier depuis Supabase"}), 400
            
            contenu_code = download_res.text

            prompt = f"""
            Tu es un expert en développement informatique et un inspecteur de code très strict pour un jeu de simulation sur Discord.
            Analyse le code suivant et attribue-lui une note sur 100 selon sa propreté, sa logique, sa complexité et l'effort fourni.
            Tu dois obligatoirement répondre UNIQUEMENT par un nombre entier entre 10 et 100.
            Aucun texte explicatif, aucun commentaire, juste le nombre.

            Voici le code à analyser :
            {contenu_code}
            """

            response = client.chat.complete(
                model="mistral-large-latest",
                messages=[{"role": "user", "content": prompt}]
            )

        # Extraction et nettoyage de la note renvoyée par Mistral
        note_texte = response.choices[0].message.content.strip()
        
        # Sécurité pour extraire uniquement les chiffres si l'IA a mis du texte par erreur
        note_nettoyee = "".join([c for c in note_texte if c.isdigit()])
        
        if not note_nettoyee:
            score = 50  # Note par défaut en cas de bug de lecture
        else:
            score = int(note_nettoyee)
            # On s'assure que la note reste bien entre 0 et 100
            score = max(0, min(100, score))

        return jsonify({"status": "success", "score": score})

    except Exception as e:
        print(f"❌ Erreur lors de l'analyse : {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Route de test (Healthcheck) pour éviter les erreurs 502 de Railway
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "message": "L'API d'analyse Mistral AI fonctionne parfaitement !"}), 200

if __name__ == '__main__':
    # Écoute sur le port configuré par Railway ou le port 5000 par défaut
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
