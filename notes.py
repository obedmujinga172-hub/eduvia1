"""
notes.py
---------
Gère :
  - les attributions : quel enseignant a le droit d'enseigner (et de noter)
    quelle matière dans quelle classe. C'est la base des permissions réelles
    sur la saisie des notes (pas seulement des boutons cachés).
  - la saisie, la modification et la lecture des notes.
  - le calcul des moyennes.
"""

from datetime import datetime
from database import obtenir_connexion

PERIODES = ["1er Trimestre", "2ème Trimestre", "3ème Trimestre"]


# ================= ATTRIBUTIONS =================

def attribuer(id_enseignant, id_classe, id_matiere):
    """Autorise un enseignant à enseigner/noter une matière dans une classe."""
    connexion = obtenir_connexion()
    connexion.execute("""
        INSERT OR IGNORE INTO attributions (id_enseignant, id_classe, id_matiere)
        VALUES (?, ?, ?)
    """, (id_enseignant, id_classe, id_matiere))
    connexion.commit()
    connexion.close()


def supprimer_attribution(id_attribution):
    connexion = obtenir_connexion()
    connexion.execute("DELETE FROM attributions WHERE id = ?", (id_attribution,))
    connexion.commit()
    connexion.close()


def lister_toutes_attributions():
    """Retourne toutes les attributions avec les noms lisibles (jointures), pour le Préfet."""
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT attributions.*,
               utilisateurs.nom_complet AS nom_enseignant,
               classes.niveau AS classe_niveau, classes.nom AS classe_nom,
               matieres.nom AS nom_matiere
        FROM attributions
        JOIN utilisateurs ON utilisateurs.id = attributions.id_enseignant
        JOIN classes ON classes.id = attributions.id_classe
        JOIN matieres ON matieres.id = attributions.id_matiere
        ORDER BY utilisateurs.nom_complet
    """).fetchall()
    connexion.close()
    return lignes


def lister_attributions_enseignant(id_enseignant):
    """Retourne les classes/matières attribuées à UN enseignant précis."""
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT attributions.*,
               classes.niveau AS classe_niveau, classes.nom AS classe_nom,
               matieres.nom AS nom_matiere
        FROM attributions
        JOIN classes ON classes.id = attributions.id_classe
        JOIN matieres ON matieres.id = attributions.id_matiere
        WHERE attributions.id_enseignant = ?
        ORDER BY classes.niveau, matieres.nom
    """, (id_enseignant,)).fetchall()
    connexion.close()
    return lignes


def enseignant_a_droit(id_enseignant, id_classe, id_matiere):
    """Vérifie qu'un enseignant a bien le droit de noter cette matière dans cette classe."""
    connexion = obtenir_connexion()
    ligne = connexion.execute("""
        SELECT 1 FROM attributions
        WHERE id_enseignant = ? AND id_classe = ? AND id_matiere = ?
    """, (id_enseignant, id_classe, id_matiere)).fetchone()
    connexion.close()
    return ligne is not None


def enseignant_a_classe(id_enseignant, id_classe):
    """Vérifie qu'un enseignant enseigne au moins une matière dans cette classe (pour consulter les résultats globaux)."""
    connexion = obtenir_connexion()
    ligne = connexion.execute("""
        SELECT 1 FROM attributions WHERE id_enseignant = ? AND id_classe = ?
    """, (id_enseignant, id_classe)).fetchone()
    connexion.close()
    return ligne is not None


# ================= NOTES =================

def enregistrer_note(id_eleve, id_matiere, id_classe, periode, valeur, id_enseignant):
    """
    Enregistre (ou met à jour si elle existe déjà) la note d'un élève
    dans une matière, pour une période donnée.
    """
    connexion = obtenir_connexion()
    connexion.execute("""
        INSERT INTO notes (id_eleve, id_matiere, id_classe, periode, valeur, id_enseignant, date_saisie)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(id_eleve, id_matiere, periode)
        DO UPDATE SET valeur = excluded.valeur,
                      id_enseignant = excluded.id_enseignant,
                      date_saisie = excluded.date_saisie
    """, (id_eleve, id_matiere, id_classe, periode, valeur, id_enseignant,
          datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    connexion.commit()
    connexion.close()


def obtenir_notes_classe_matiere(id_classe, id_matiere, periode):
    """Retourne, pour chaque élève de la classe, sa note existante (ou None) dans cette matière/période."""
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT eleves.id AS id_eleve, eleves.nom, eleves.postnom, eleves.prenom,
               notes.valeur
        FROM eleves
        LEFT JOIN notes ON notes.id_eleve = eleves.id
                        AND notes.id_matiere = ? AND notes.periode = ?
        WHERE eleves.id_classe = ? AND eleves.statut = 'ACTIF'
        ORDER BY eleves.nom
    """, (id_matiere, periode, id_classe)).fetchall()
    connexion.close()
    return lignes


def obtenir_notes_eleve(id_eleve, periode=None):
    """Retourne toutes les notes d'un élève (avec le nom de la matière), pour une période ou toutes."""
    connexion = obtenir_connexion()
    if periode:
        lignes = connexion.execute("""
            SELECT notes.*, matieres.nom AS nom_matiere
            FROM notes JOIN matieres ON matieres.id = notes.id_matiere
            WHERE notes.id_eleve = ? AND notes.periode = ?
            ORDER BY matieres.nom
        """, (id_eleve, periode)).fetchall()
    else:
        lignes = connexion.execute("""
            SELECT notes.*, matieres.nom AS nom_matiere
            FROM notes JOIN matieres ON matieres.id = notes.id_matiere
            WHERE notes.id_eleve = ?
            ORDER BY notes.periode, matieres.nom
        """, (id_eleve,)).fetchall()
    connexion.close()
    return lignes


def calculer_moyenne(id_eleve, periode):
    """Retourne la moyenne d'un élève sur une période (None si aucune note)."""
    notes_eleve = obtenir_notes_eleve(id_eleve, periode)
    if not notes_eleve:
        return None
    return round(sum(n["valeur"] for n in notes_eleve) / len(notes_eleve), 2)


def obtenir_resultats_classe(id_classe, periode):
    """
    Retourne, pour chaque élève actif de la classe, ses notes par matière
    et sa moyenne pour la période donnée. Utile pour la vue "résultats de classe".
    """
    connexion = obtenir_connexion()
    eleves = connexion.execute("""
        SELECT * FROM eleves WHERE id_classe = ? AND statut = 'ACTIF' ORDER BY nom
    """, (id_classe,)).fetchall()
    connexion.close()

    resultats = []
    for eleve in eleves:
        notes_eleve = obtenir_notes_eleve(eleve["id"], periode)
        moyenne = calculer_moyenne(eleve["id"], periode)
        resultats.append({"eleve": eleve, "notes": notes_eleve, "moyenne": moyenne})
    return resultats
