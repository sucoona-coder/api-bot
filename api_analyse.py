from flask import Flask, request, jsonify
import os
import requests
from PIL import Image
import io
import re

app = Flask(__name__)
API_KEY = os.environ.get("ANALYSIS_API_KEY")

# Métiers et critères d'analyse
METIERS_CRITERES = {
    "code": {
        "extensions": [".py", ".js", ".java", ".cpp", ".c", ".txt", ".html", ".css"],
        "max_score": 100,
        "feedback_exemples": {
            90: "Code exceptionnel ! Bien structuré, commenté et optimisé.",
            70: "Bon code, mais pourrait être amélioré avec plus de commentaires.",
            50: "Code fonctionnel, mais peu lisible. Ajoutez des docstrings.",
            30: "Code minimaliste. Pensez à la maintenabilité.",
            10: "Code incomplet ou mal formaté."
        }
    },
    "image": {
        "extensions": [".png", ".jpg", ".jpeg", ".gif", ".svg"],
        "max_score": 100,
        "feedback_exemples": {
            90: "Image professionnelle ! Résolution et couleurs optimales.",
            70: "Belle image, mais la résolution pourrait être améliorée.",
            50: "Image correcte, mais peu originale.",
            30: "Image basique. Ajoutez des détails.",
            10: "Image floue ou mal recadrée."
        }
    },
    "text": {
        "extensions": [".txt"],
        "max_score": 100,
        "feedback_exemples": {
            90: "Cosignes complètes et claires ! Excellente modération.",
            70: "Bon travail, mais certaines règles manquent de précision.",
            50: "Cosignes basiques. Ajoutez des exemples.",
            30: "Texte trop court ou peu détaillé.",
            10: "Cosignes incomplètes ou illisibles."
        }
    }
}

def analyser_code(code: str) -> tuple:
    """Analyse un fichier de code."""
    lignes = [l for l in code.splitlines() if l.strip()]  # Ignore les lignes purement vides
    nb_lignes = len(lignes)
    if nb_lignes == 0:
        return 10, METIERS_CRITERES["code"]["feedback_exemples"][10]

    nb_commentaires = sum(1 for ligne in lignes if ligne.strip().startswith(("#", "//", "/*", "*", "*/")))
    nb_fonctions = sum(1 for ligne in lignes if re.search(r"\b(def|function|class)\b", ligne))
    ratio_commentaires = (nb_commentaires / nb_lignes) * 100

    # Recalibrage des scores pour éviter la triche (ex: 500 lignes vides avec des #)
    score_lignes = min(30, nb_lignes * 0.15)  # Demande ~200 lignes pour le max
    
    # Le ratio de commentaires optimal en entreprise se situe entre 15% et 35%
    if 15 <= ratio_commentaires <= 40:
        score_commentaires = 30
    else:
        score_commentaires = min(30, ratio_commentaires * 0.5)

    score_fonctions = min(20, nb_fonctions * 4)  # 5 fonctions ou classes = max points
    score_longueur = min(20, (sum(len(ligne) for ligne in lignes) / nb_lignes) * 0.4)

    score = int(score_lignes + score_commentaires + score_fonctions + score_longueur)
    score = max(10, min(100, score))

    if score >= 90:
        feedback = METIERS_CRITERES["code"]["feedback_exemples"][90]
    elif score >= 70:
        feedback = METIERS_CRITERES["code"]["feedback_exemples"][70]
    elif score >= 50:
        feedback = METIERS_CRITERES["code"]["feedback_exemples"][50]
    elif score >= 30:
        feedback = METIERS_CRITERES["code"]["feedback_exemples"][30]
    else:
        feedback = METIERS_CRITERES["code"]["feedback_exemples"][10]

    return score, feedback

def analyser_image(image_bytes: bytes) -> tuple:
    """Analyse une image."""
    try:
        img = Image.open(io.BytesIO(image_bytes))
        width, height = img.size
        aspect_ratio = width / height
        pixels_total = width * height

        # Correction de la formule : la formule originale atteignait 40 pts dès 100x100px.
        # Nouvelle formule basée sur les standards du web (Max points à partir de ~1M de pixels, ex: 1280x720)
        score_resolution = min(40, (pixels_total / 1_000_000) * 40)
        score_resolution = max(5, score_resolution)

        score_ratio = min(20, 20 if 0.5 <= aspect_ratio <= 2.0 else 10)
        score_mode = 20 if img.mode in ["RGB", "RGBA"] else 10
        
        # Attribution d'un score réaliste basé sur le poids (ex: si > 50 Ko, l'image a de la donnée)
        score_taille = min(20, (len(image_bytes) / 50_000) * 20)
        score_taille = max(5, score_taille)

        score = int(score_resolution + score_ratio + score_mode + score_taille)
        score = max(10, min(100, score))

        if score >= 90:
            feedback = METIERS_CRITERES["image"]["feedback_exemples"][90]
        elif score >= 70:
            feedback = METIERS_CRITERES["image"]["feedback_exemples"][70]
        elif score >= 50:
            feedback = METIERS_CRITERES["image"]["feedback_exemples"][50]
        elif score >= 30:
            feedback = METIERS_CRITERES["image"]["feedback_exemples"][30]
        else:
            feedback = METIERS_CRITERES["image"]["feedback_exemples"][10]

        return score, feedback
    except Exception as e:
        return 10, f"Erreur d'analyse : {str(e)}"

def analyser_texte(texte: str) -> tuple:
    """Analyse un fichier texte (cosignes)."""
    mots = texte.split()
    nb_mots = len(mots)
    if nb_mots == 0:
        return 10, METIERS_CRITERES["text"]["feedback_exemples"][10]

    nb_lignes = texte.count("\n") + 1
    nb_caracteres = len(texte)

    score_mots = min(40, nb_mots * 0.2)  # Max points à partir de 200 mots
    score_lignes = min(30, nb_lignes * 1.5)
    score_longueur = min(20, (nb_caracteres / nb_mots) * 2)
    
    mots_cles = ["règle", "interdit", "sanction", "modération", "comportement", "respect", "ban", "warn"]
    score_mots_cles = min(10, sum(1 for kw in mots_cles if kw in texte.lower()) * 2)  # 5 mots clés trouvés = max
    
    score = int(score_mots + score_lignes + score_longueur + score_mots_cles)
    score = max(10, min(100, score))

    if score >= 90:
        feedback = METIERS_CRITERES["text"]["feedback_exemples"][90]
    elif score >= 70:
        feedback = METIERS_CRITERES["text"]["feedback_exemples"][70]
    elif score >= 50:
        feedback = METIERS_CRITERES["text"]["feedback_exemples"][50]
    elif score >= 30:
        feedback = METIERS_CRITERES["text"]["feedback_exemples"][30]
    else:
        feedback = METIERS_CRITERES["text"]["feedback_exemples"][10]

    return score, feedback

@app.route("/analyse", methods=["POST"])
def analyse():
    auth = request.headers.get("Authorization")
    if not API_KEY or auth != f"Bearer {API_KEY}":
        return jsonify({"error": "Clé API invalide ou absente"}), 403

    data = request.json or {}
    file_url = data.get("file_url")
    file_type = data.get("file_type")

    if not file_url or not file_type:
        return jsonify({"error": "file_url et file_type requis"}), 400

    if file_type not in METIERS_CRITERES:
        return jsonify({"error": "Type de fichier non supporté"}), 400

    try:
        # Sécurité : Protection contre le DoS (Limite de téléchargement à 6 Mo max en streaming)
        response = requests.get(file_url, stream=True, timeout=15)
        response.raise_for_status()
        
        content_buffer = bytearray()
        max_bytes = 6 * 1024 * 1024  # 6 Mo
        for chunk in response.iter_content(chunk_size=8192):
            content_buffer.extend(chunk)
            if len(content_buffer) > max_bytes:
                return jsonify({"error": "Le fichier téléchargé dépasse la limite maximale autorisée de 6 Mo."}), 413
        
        content = bytes(content_buffer)

        # Analyser selon le type
        if file_type == "code":
            score, feedback = analyser_code(content.decode("utf-8", errors="ignore"))
        elif file_type == "image":
            score, feedback = analyser_image(content)
        elif file_type == "text":
            score, feedback = analyser_texte(content.decode("utf-8", errors="ignore"))
        else:
            return jsonify({"error": "Type inconnu"}), 400

        return jsonify({"score": score, "feedback": feedback})

    except requests.RequestException as e:
        return jsonify({"error": f"Erreur téléchargement: {str(e)}"}), 400
    except Exception as e:
        return jsonify({"error": f"Erreur interne d'analyse: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
