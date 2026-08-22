"""
models.py
----------
Ce fichier contient toutes les fonctions qui touchent aux données
des élèves : ajouter, lister, obtenir un élève, modifier, supprimer.

C'est ici, et nulle part ailleurs, qu'on écrit du SQL pour les élèves.
"""

from datetime import date, datetime
from database import obtenir_connexion

# Libellés affichés à l'écran pour chaque statut (stocké sans accent en base,
# pour éviter les soucis d'encodage dans la contrainte CHECK SQL)
NOMS_STATUTS = {
    "ACTIF": "Actif",
    "TRANSFERE": "Transféré",
    "DIPLOME": "Diplômé",
    "EXCLU": "Exclu",
    "ARCHIVE": "Archivé",
    "INACTIF": "Inactif",
}

# Colonnes communes utilisées par plusieurs requêtes ci-dessous, avec une
# jointure vers 'classes', 'options' et 'annees_scolaires' pour afficher des
# noms lisibles plutôt que de simples identifiants numériques.
SELECT_ELEVE_AVEC_CLASSE = """
    SELECT eleves.*,
           classes.niveau AS classe_niveau,
           classes.nom AS classe_nom,
           options.nom AS option_nom,
           annees_scolaires.libelle AS annee_scolaire
    FROM eleves
    LEFT JOIN classes ON classes.id = eleves.id_classe
    LEFT JOIN options ON options.id = classes.id_option
    LEFT JOIN annees_scolaires ON annees_scolaires.id = classes.id_annee_scolaire
"""


def ajouter_eleve(donnees):
    """
    Ajoute un nouvel élève dans la base de données.
    'donnees' est un dictionnaire contenant les informations du formulaire.
    """
    connexion = obtenir_connexion()
    curseur = connexion.execute("""
        INSERT INTO eleves (
            matricule, nom, postnom, prenom, sexe,
            date_naissance, lieu_naissance, id_classe,
            nom_parent, contact_parent, adresse, date_inscription
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        donnees["matricule"],
        donnees["nom"],
        donnees["postnom"],
        donnees["prenom"],
        donnees["sexe"],
        donnees["date_naissance"],
        donnees["lieu_naissance"],
        donnees["id_classe"] or None,
        donnees["nom_parent"],
        donnees["contact_parent"],
        donnees["adresse"],
        date.today().isoformat(),
    ))
    id_nouvel_eleve = curseur.lastrowid
    connexion.commit()
    connexion.close()

    ajouter_evenement_historique(id_nouvel_eleve, "Inscription", f"Matricule {donnees['matricule']}")
    return id_nouvel_eleve


def obtenir_tous_les_eleves(recherche=None):
    """
    Retourne la liste de tous les élèves (avec le nom de leur classe/option),
    triée par niveau puis par nom.
    Si 'recherche' est fourni, filtre par nom, postnom ou matricule.
    """
    connexion = obtenir_connexion()
    if recherche:
        motif = f"%{recherche}%"
        lignes = connexion.execute(
            SELECT_ELEVE_AVEC_CLASSE + """
            WHERE eleves.nom LIKE ? OR eleves.postnom LIKE ? OR eleves.matricule LIKE ?
            ORDER BY classes.niveau, eleves.nom
        """, (motif, motif, motif)).fetchall()
    else:
        lignes = connexion.execute(
            SELECT_ELEVE_AVEC_CLASSE + " ORDER BY classes.niveau, eleves.nom"
        ).fetchall()
    connexion.close()
    return lignes


def obtenir_eleve_par_id(id_eleve):
    """Retourne un seul élève (avec classe/option) à partir de son identifiant."""
    connexion = obtenir_connexion()
    eleve = connexion.execute(
        SELECT_ELEVE_AVEC_CLASSE + " WHERE eleves.id = ?", (id_eleve,)
    ).fetchone()
    connexion.close()
    return eleve


def modifier_eleve(id_eleve, donnees):
    """Met à jour les informations d'un élève existant."""
    connexion = obtenir_connexion()
    connexion.execute("""
        UPDATE eleves SET
            matricule = ?, nom = ?, postnom = ?, prenom = ?, sexe = ?,
            date_naissance = ?, lieu_naissance = ?, id_classe = ?,
            nom_parent = ?, contact_parent = ?, adresse = ?
        WHERE id = ?
    """, (
        donnees["matricule"],
        donnees["nom"],
        donnees["postnom"],
        donnees["prenom"],
        donnees["sexe"],
        donnees["date_naissance"],
        donnees["lieu_naissance"],
        donnees["id_classe"] or None,
        donnees["nom_parent"],
        donnees["contact_parent"],
        donnees["adresse"],
        id_eleve,
    ))
    connexion.commit()
    connexion.close()


def supprimer_eleve(id_eleve):
    """Supprime définitivement un élève de la base de données."""
    connexion = obtenir_connexion()
    connexion.execute("DELETE FROM eleves WHERE id = ?", (id_eleve,))
    connexion.commit()
    connexion.close()


def mettre_a_jour_photo_eleve(id_eleve, chemin_photo):
    connexion = obtenir_connexion()
    connexion.execute("UPDATE eleves SET chemin_photo = ? WHERE id = ?", (chemin_photo, id_eleve))
    connexion.commit()
    connexion.close()


def compter_eleves():
    """Retourne le nombre total d'élèves inscrits (utile pour le tableau de bord)."""
    connexion = obtenir_connexion()
    total = connexion.execute("SELECT COUNT(*) AS total FROM eleves").fetchone()["total"]
    connexion.close()
    return total


def obtenir_eleves_par_classe(id_classe):
    """Retourne les élèves actifs d'une classe donnée, triés par nom (utile pour la saisie des notes)."""
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT * FROM eleves WHERE id_classe = ? AND statut = 'ACTIF' ORDER BY nom
    """, (id_classe,)).fetchall()
    connexion.close()
    return lignes


# ================= STATUT DE L'ELEVE =================

def changer_statut_eleve(id_eleve, nouveau_statut):
    """Change le statut d'un élève (voir NOMS_STATUTS pour les valeurs possibles)."""
    connexion = obtenir_connexion()
    connexion.execute("UPDATE eleves SET statut = ? WHERE id = ?", (nouveau_statut, id_eleve))
    connexion.commit()
    connexion.close()


# ================= HISTORIQUE SCOLAIRE =================
# Distinct du journal d'audit global (audit.py) : celui-ci ne concerne que
# le parcours d'UN élève, et reste consultable même si son compte est
# désactivé ou si l'élève a quitté l'école.

def ajouter_evenement_historique(id_eleve, evenement, details=""):
    connexion = obtenir_connexion()
    connexion.execute("""
        INSERT INTO historique_eleve (id_eleve, evenement, details, date_heure)
        VALUES (?, ?, ?, ?)
    """, (id_eleve, evenement, details, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    connexion.commit()
    connexion.close()


def obtenir_historique_eleve(id_eleve):
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT * FROM historique_eleve WHERE id_eleve = ? ORDER BY id DESC
    """, (id_eleve,)).fetchall()
    connexion.close()
    return lignes
