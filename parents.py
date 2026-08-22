"""
parents.py
-----------
Gère le lien entre un compte "parent/tuteur" et les élèves (enfants)
qui lui sont associés. Un parent peut avoir plusieurs enfants inscrits.
"""

from database import obtenir_connexion


def lier_enfant(id_parent, id_eleve):
    """Associe un élève à un compte parent. Ne fait rien si le lien existe déjà."""
    connexion = obtenir_connexion()
    connexion.execute("""
        INSERT OR IGNORE INTO parents_eleves (id_parent, id_eleve)
        VALUES (?, ?)
    """, (id_parent, id_eleve))
    connexion.commit()
    connexion.close()


def obtenir_enfants(id_parent):
    """Retourne la liste des fiches élèves (avec classe/option) associées à un compte parent."""
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT eleves.*, classes.niveau AS classe_niveau, classes.nom AS classe_nom, options.nom AS option_nom
        FROM eleves
        JOIN parents_eleves ON parents_eleves.id_eleve = eleves.id
        LEFT JOIN classes ON classes.id = eleves.id_classe
        LEFT JOIN options ON options.id = classes.id_option
        WHERE parents_eleves.id_parent = ?
        ORDER BY eleves.nom
    """, (id_parent,)).fetchall()
    connexion.close()
    return lignes


def parent_est_lie_a_eleve(id_parent, id_eleve):
    """Vérifie qu'un parent a bien le droit de consulter cet élève précis."""
    connexion = obtenir_connexion()
    ligne = connexion.execute("""
        SELECT 1 FROM parents_eleves WHERE id_parent = ? AND id_eleve = ?
    """, (id_parent, id_eleve)).fetchone()
    connexion.close()
    return ligne is not None
