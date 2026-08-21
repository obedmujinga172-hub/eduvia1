"""
presences.py
-------------
Gère l'enregistrement des présences (Présent / Absent / Retard) et leur
consultation par l'administration. Utilise les mêmes attributions
enseignant/classe/matière que le module notes.py pour les permissions.
"""

from datetime import date, datetime
from database import obtenir_connexion

NOMS_STATUTS = {
    "PRESENT": "Présent",
    "ABSENT": "Absent",
    "RETARD": "Retard",
}


def enregistrer_presence(id_eleve, id_classe, id_matiere, id_enseignant, date_jour, statut):
    """Enregistre (ou met à jour) la présence d'un élève pour une matière, à une date donnée."""
    connexion = obtenir_connexion()
    connexion.execute("""
        INSERT INTO presences (id_eleve, id_classe, id_matiere, id_enseignant, date_jour, statut, date_saisie)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id_eleve, id_matiere, date_jour)
        DO UPDATE SET statut = excluded.statut,
                      id_enseignant = excluded.id_enseignant,
                      date_saisie = excluded.date_saisie
    """, (id_eleve, id_classe, id_matiere, id_enseignant, date_jour, statut,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    connexion.commit()
    connexion.close()


def obtenir_presences_classe_matiere_date(id_classe, id_matiere, date_jour):
    """Pour l'appel d'une classe : chaque élève actif avec son statut existant pour ce jour (ou None)."""
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT eleves.id AS id_eleve, eleves.nom, eleves.postnom, eleves.prenom,
               presences.statut
        FROM eleves
        LEFT JOIN presences ON presences.id_eleve = eleves.id
                            AND presences.id_matiere = ? AND presences.date_jour = ?
        WHERE eleves.id_classe = ? AND eleves.statut = 'ACTIF'
        ORDER BY eleves.nom
    """, (id_matiere, date_jour, id_classe)).fetchall()
    connexion.close()
    return lignes


def obtenir_historique_eleve(id_eleve):
    """Tout l'historique de présence d'un élève (toutes matières), du plus récent au plus ancien."""
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT presences.*, matieres.nom AS nom_matiere
        FROM presences
        LEFT JOIN matieres ON matieres.id = presences.id_matiere
        WHERE presences.id_eleve = ?
        ORDER BY presences.date_jour DESC
    """, (id_eleve,)).fetchall()
    connexion.close()
    return lignes


def obtenir_historique_classe(id_classe, date_debut=None, date_fin=None):
    """Historique de présence de toute une classe, avec filtre optionnel de dates (pour l'administration)."""
    connexion = obtenir_connexion()
    requete = """
        SELECT presences.*, eleves.nom, eleves.postnom, eleves.prenom, matieres.nom AS nom_matiere
        FROM presences
        JOIN eleves ON eleves.id = presences.id_eleve
        LEFT JOIN matieres ON matieres.id = presences.id_matiere
        WHERE presences.id_classe = ?
    """
    parametres = [id_classe]
    if date_debut:
        requete += " AND presences.date_jour >= ?"
        parametres.append(date_debut)
    if date_fin:
        requete += " AND presences.date_jour <= ?"
        parametres.append(date_fin)
    requete += " ORDER BY presences.date_jour DESC, eleves.nom"
    lignes = connexion.execute(requete, parametres).fetchall()
    connexion.close()
    return lignes


def compter_absences_retards(id_eleve):
    """Retourne (nombre d'absences, nombre de retards) pour un élève, utile en résumé rapide."""
    connexion = obtenir_connexion()
    absences = connexion.execute(
        "SELECT COUNT(*) AS total FROM presences WHERE id_eleve = ? AND statut = 'ABSENT'", (id_eleve,)
    ).fetchone()["total"]
    retards = connexion.execute(
        "SELECT COUNT(*) AS total FROM presences WHERE id_eleve = ? AND statut = 'RETARD'", (id_eleve,)
    ).fetchone()["total"]
    connexion.close()
    return absences, retards
