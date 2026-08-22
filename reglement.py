"""
reglement.py
-------------
Gère le règlement d'ordre intérieur : un seul fichier PDF, stocké sur
disque à un emplacement fixe, remplacé à chaque nouvel import.
Reste volontairement simple : pas d'historique de versions.
"""

import os
from datetime import date
from database import obtenir_connexion

CHEMIN_FICHIER = os.path.join("static", "reglement", "reglement.pdf")


def obtenir_infos():
    connexion = obtenir_connexion()
    ligne = connexion.execute("SELECT * FROM reglement_interieur WHERE id = 1").fetchone()
    connexion.close()
    return ligne


def fichier_existe():
    return os.path.exists(CHEMIN_FICHIER)


def remplacer_fichier(fichier_televerse):
    """Enregistre le nouveau règlement, en écrasant l'ancien s'il existe."""
    os.makedirs(os.path.dirname(CHEMIN_FICHIER), exist_ok=True)
    fichier_televerse.save(CHEMIN_FICHIER)

    connexion = obtenir_connexion()
    connexion.execute("""
        UPDATE reglement_interieur SET nom_fichier_original = ?, date_import = ? WHERE id = 1
    """, (fichier_televerse.filename, date.today().isoformat()))
    connexion.commit()
    connexion.close()
