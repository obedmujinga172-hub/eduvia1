"""
photos.py
----------
Enregistre une photo téléversée (élève ou compte utilisateur) : valide
que c'est bien une image, la redimensionne pour ne pas gonfler l'espace
disque, et l'enregistre toujours au format JPEG à un chemin fixe
(écrase l'ancienne photo s'il y en avait une).
"""

import os
from PIL import Image, UnidentifiedImageError

TAILLE_MAX_PIXELS = 500  # largeur/hauteur maximale, le ratio est conservé


def enregistrer_photo(fichier_televerse, dossier, nom_base):
    """
    Enregistre la photo dans 'dossier/nom_base.jpg'.
    Retourne le chemin du fichier si succès, ou None si le fichier n'est
    pas une image valide (pas d'exception levée : on gère l'erreur nous-mêmes).
    """
    if not fichier_televerse or not fichier_televerse.filename:
        return None

    try:
        image = Image.open(fichier_televerse.stream)
        image.verify()  # vérifie que le fichier n'est pas corrompu/falsifié
        fichier_televerse.stream.seek(0)
        image = Image.open(fichier_televerse.stream).convert("RGB")
    except (UnidentifiedImageError, OSError):
        return None

    image.thumbnail((TAILLE_MAX_PIXELS, TAILLE_MAX_PIXELS))

    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, f"{nom_base}.jpg")
    image.save(chemin, "JPEG", quality=85)
    return chemin
