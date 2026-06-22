import os
import requests
from flask import Flask, request, jsonify
from mistralai import Mistral

app = Flask(__name__)

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
ANALYSIS_API_KEY = os.getenv("ANALYSIS_API_KEY")

if not MISTRAL_API_KEY:
    print("⚠️ ATTENTION : La variable MISTRAL_API_KEY n'est pas configurée !")

@app.route('/analyse', methods=['POST'])
def analyse_submission():
    auth_header = request.headers.get("Authorization")
    if not auth_header or auth_header != f"Bearer {ANALYSIS_API_KEY}":
        return jsonify({"status": "error", "message": "Accès non autorisé"}), 401

    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "Aucune donnée reçue"}), 400

    file_url = data.get("file_url")
    file_type = data.get("file_type", "code")

    if not file_url:
        return jsonify({"status": "error", "message": "URL du fichier manquante"}), 400

    try:
        client = Mistral(api_key=MISTRAL_API_KEY)

        # --- CAS 1 : ANALYSE D'UNE IMAGE ---
        if file_type == "image":
            prompt = """
            Tu es un inspecteur et designer critique pour un jeu de simulation d'entreprise sur Discord.
            Analyse cette image qui est une soumission de travail d'un joueur.
            Évalue la qualité visuelle, l'effort fourni et la pertinence.
            
            Tu dois obligatoirement répondre sous ce format JSON strict :
            {
                "score": un nombre entier entre 10 et 100,
                "feedback": "Une courte phrase de feedback constructive en français pour le joueur sur son design."
            }
            Ne renvoie aucun autre texte que le JSON brut.
            """

            response = client.chat.complete(
                model="pixtral-12b-latest",
                response_format={"type": "json_object"}, # Force le format JSON
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
            download_res = requests.get(file_url, timeout=10)
            if download_res.status_code != 200:
                return jsonify({"status": "error", "message": "Impossible de télécharger le fichier"}), 400
            
            contenu_code = download_res.text

            prompt = f"""
            Tu es un expert en développement informatique et un inspecteur de code très strict pour un jeu de simulation sur Discord.
            Analyse le code suivant et attribue-lui une note sur 100 selon sa propreté, sa logique, sa complexité et l'effort fourni.
            
            Tu dois obligatoirement répondre sous ce format JSON strict :
            {{
                "score": un nombre entier entre 10 et 100,
                "feedback": "Une courte phrase d'évaluation en français expliquant les points forts et faibles du code."
            }}
            Ne renvoie aucun autre texte que le JSON brut.

            Voici le code à analyser :
            {contenu_code}
            """

            response = client.chat.complete(
                model="mistral-large-latest",
                response_format={"type": "json_object"}, # Force le format JSON
                messages=[{"role": "user", "content": prompt}]
            )

        # Extraction des données JSON structurées renvoyées par Mistral
        import json
        resultat_ia = json.loads(response.choices[0].message.content.strip())
        
        score = int(resultat_ia.get("score", 50))
        score = max(0, min(100, score)) # Sécurité
        feedback = resultat_ia.get("feedback", "Analyse qualitative effectuée.")

        # ENVOI CORRIGÉ : On fournit maintenant le score ET le feedback demandés par le bot !
        return jsonify({
            "status": "success", 
            "score": score,
            "feedback": feedback
        })

    except Exception as e:
        print(f"❌ Erreur lors de l'analyse : {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "online", "message": "L'API d'analyse Mistral AI fonctionne parfaitement !"}), 200

if __name__ == '__main__':
    port = int(os.getenv("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
