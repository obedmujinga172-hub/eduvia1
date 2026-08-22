"""
organisation.py
-----------------
Gère la configuration de l'organisation scolaire :
années scolaires, options (filières), classes, matières.

Ce sont les "briques" que le Préfet configure une fois, et que les
autres modules (élèves, notes, emploi du temps...) viennent utiliser.
"""

from database import obtenir_connexion


# ================= ANNEES SCOLAIRES =================

def ajouter_annee_scolaire(libelle):
    connexion = obtenir_connexion()
    connexion.execute("INSERT INTO annees_scolaires (libelle, active) VALUES (?, 0)", (libelle.strip(),))
    connexion.commit()
    connexion.close()


def lister_annees_scolaires():
    connexion = obtenir_connexion()
    lignes = connexion.execute("SELECT * FROM annees_scolaires ORDER BY libelle DESC").fetchall()
    connexion.close()
    return lignes


def activer_annee_scolaire(id_annee):
    """Rend cette année scolaire active, et désactive automatiquement les autres."""
    connexion = obtenir_connexion()
    connexion.execute("UPDATE annees_scolaires SET active = 0")
    connexion.execute("UPDATE annees_scolaires SET active = 1 WHERE id = ?", (id_annee,))
    connexion.commit()
    connexion.close()


def obtenir_annee_active():
    connexion = obtenir_connexion()
    ligne = connexion.execute("SELECT * FROM annees_scolaires WHERE active = 1").fetchone()
    connexion.close()
    return ligne


# ================= OPTIONS (filières) =================

def ajouter_option(nom, description=""):
    connexion = obtenir_connexion()
    connexion.execute("INSERT INTO options (nom, description) VALUES (?, ?)", (nom.strip(), description.strip()))
    connexion.commit()
    connexion.close()


def lister_options():
    connexion = obtenir_connexion()
    lignes = connexion.execute("SELECT * FROM options ORDER BY nom").fetchall()
    connexion.close()
    return lignes


def supprimer_option(id_option):
    connexion = obtenir_connexion()
    connexion.execute("DELETE FROM options WHERE id = ?", (id_option,))
    connexion.commit()
    connexion.close()


# ================= CLASSES =================

NIVEAUX_SECONDAIRE = ["7ème CTEB", "1ère", "2ème", "3ème", "4ème", "5ème", "6ème"]


def ajouter_classe(niveau, nom, id_option, id_annee_scolaire):
    connexion = obtenir_connexion()
    connexion.execute("""
        INSERT INTO classes (niveau, nom, id_option, id_annee_scolaire)
        VALUES (?, ?, ?, ?)
    """, (niveau, nom.strip(), id_option or None, id_annee_scolaire))
    connexion.commit()
    connexion.close()


def lister_classes(id_annee_scolaire=None):
    """
    Retourne les classes avec le nom de leur option (jointure), triées par niveau.
    Si id_annee_scolaire est fourni, ne retourne que les classes de cette année.
    """
    connexion = obtenir_connexion()
    requete = """
        SELECT classes.*, options.nom AS nom_option, annees_scolaires.libelle AS annee
        FROM classes
        LEFT JOIN options ON options.id = classes.id_option
        JOIN annees_scolaires ON annees_scolaires.id = classes.id_annee_scolaire
    """
    if id_annee_scolaire:
        requete += " WHERE classes.id_annee_scolaire = ?"
        lignes = connexion.execute(requete + " ORDER BY classes.niveau, classes.nom", (id_annee_scolaire,)).fetchall()
    else:
        lignes = connexion.execute(requete + " ORDER BY classes.niveau, classes.nom").fetchall()
    connexion.close()
    return lignes


def supprimer_classe(id_classe):
    connexion = obtenir_connexion()
    connexion.execute("DELETE FROM classes WHERE id = ?", (id_classe,))
    connexion.commit()
    connexion.close()


# ================= MATIERES =================

def ajouter_matiere(nom, description=""):
    connexion = obtenir_connexion()
    connexion.execute("INSERT INTO matieres (nom, description) VALUES (?, ?)", (nom.strip(), description.strip()))
    connexion.commit()
    connexion.close()


def lister_matieres():
    connexion = obtenir_connexion()
    lignes = connexion.execute("SELECT * FROM matieres ORDER BY nom").fetchall()
    connexion.close()
    return lignes


def supprimer_matiere(id_matiere):
    connexion = obtenir_connexion()
    connexion.execute("DELETE FROM matieres WHERE id = ?", (id_matiere,))
    connexion.commit()
    connexion.close()
