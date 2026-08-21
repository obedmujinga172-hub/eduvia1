"""
audit.py
---------
Enregistre un historique des actions sensibles effectuées dans EDUVIA
(création/modification/suppression de données importantes, gestion des
comptes, connexions...).

Utilisation dans une route :

    audit.enregistrer(utilisateur, "Ajout d'un élève", f"Matricule {matricule}")
"""

from datetime import datetime
from database import obtenir_connexion


def enregistrer(utilisateur, action, details=""):
    """
    Ajoute une ligne dans le journal d'activités.
    'utilisateur' est l'utilisateur connecté qui a effectué l'action
    (objet Utilisateur, voir utilisateurs.py).
    """
    connexion = obtenir_connexion()
    connexion.execute("""
        INSERT INTO journal_activites (id_utilisateur, nom_utilisateur, action, details, date_heure)
        VALUES (?, ?, ?, ?, ?)
    """, (
        utilisateur.id,
        f"{utilisateur.nom_complet} ({utilisateur.nom_role})",
        action,
        details,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    connexion.commit()
    connexion.close()


def obtenir_journal(limite=200):
    """Retourne les dernières actions enregistrées, les plus récentes en premier."""
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT * FROM journal_activites
        ORDER BY id DESC
        LIMIT ?
    """, (limite,)).fetchall()
    connexion.close()
    return lignes
