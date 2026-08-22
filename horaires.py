"""
horaires.py
------------
Gère l'emploi du temps : des créneaux (jour + heure) rattachés à une
attribution existante (enseignant + classe + matière, voir notes.py).
Détecte les conflits (même classe ou même enseignant déjà occupé sur
un créneau qui se chevauche).
"""

from database import obtenir_connexion

JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi"]

# Colonnes communes avec les jointures nécessaires pour afficher un
# horaire de façon lisible (nom d'enseignant, classe, matière).
SELECT_HORAIRE = """
    SELECT horaires.*,
           attributions.id_classe, attributions.id_matiere, attributions.id_enseignant,
           classes.niveau AS classe_niveau, classes.nom AS classe_nom,
           matieres.nom AS nom_matiere,
           utilisateurs.nom_complet AS nom_enseignant
    FROM horaires
    JOIN attributions ON attributions.id = horaires.id_attribution
    JOIN classes ON classes.id = attributions.id_classe
    JOIN matieres ON matieres.id = attributions.id_matiere
    JOIN utilisateurs ON utilisateurs.id = attributions.id_enseignant
"""


def _se_chevauchent(debut1, fin1, debut2, fin2):
    """Vrai si les créneaux [debut1, fin1] et [debut2, fin2] (heures 'HH:MM') se chevauchent."""
    return debut1 < fin2 and debut2 < fin1


def verifier_conflit(id_classe, id_enseignant, jour, heure_debut, heure_fin, exclure_id=None):
    """
    Vérifie qu'aucun autre créneau, le même jour, ne chevauche cet horaire
    pour la même classe (elle ne peut pas avoir 2 cours en même temps)
    ou pour le même enseignant (il ne peut pas être à 2 endroits à la fois).
    Retourne un message d'erreur, ou None s'il n'y a pas de conflit.
    """
    connexion = obtenir_connexion()
    lignes = connexion.execute(SELECT_HORAIRE + " WHERE horaires.jour = ?", (jour,)).fetchall()
    connexion.close()

    for ligne in lignes:
        if exclure_id and ligne["id"] == exclure_id:
            continue
        if not _se_chevauchent(heure_debut, heure_fin, ligne["heure_debut"], ligne["heure_fin"]):
            continue
        if ligne["id_classe"] == id_classe:
            return f"Cette classe a déjà un cours ({ligne['nom_matiere']}) sur ce créneau."
        if ligne["id_enseignant"] == id_enseignant:
            return f"{ligne['nom_enseignant']} a déjà cours ailleurs sur ce créneau."
    return None


def ajouter_horaire(id_attribution, jour, heure_debut, heure_fin):
    connexion = obtenir_connexion()
    connexion.execute("""
        INSERT INTO horaires (id_attribution, jour, heure_debut, heure_fin)
        VALUES (?, ?, ?, ?)
    """, (id_attribution, jour, heure_debut, heure_fin))
    connexion.commit()
    connexion.close()


def supprimer_horaire(id_horaire):
    connexion = obtenir_connexion()
    connexion.execute("DELETE FROM horaires WHERE id = ?", (id_horaire,))
    connexion.commit()
    connexion.close()


def lister_tous_horaires():
    connexion = obtenir_connexion()
    lignes = connexion.execute(SELECT_HORAIRE + " ORDER BY horaires.jour, horaires.heure_debut").fetchall()
    connexion.close()
    return _trier_par_jour(lignes)


def lister_horaires_classe(id_classe):
    connexion = obtenir_connexion()
    lignes = connexion.execute(
        SELECT_HORAIRE + " WHERE attributions.id_classe = ? ORDER BY horaires.jour, horaires.heure_debut",
        (id_classe,)
    ).fetchall()
    connexion.close()
    return _trier_par_jour(lignes)


def lister_horaires_enseignant(id_enseignant):
    connexion = obtenir_connexion()
    lignes = connexion.execute(
        SELECT_HORAIRE + " WHERE attributions.id_enseignant = ? ORDER BY horaires.jour, horaires.heure_debut",
        (id_enseignant,)
    ).fetchall()
    connexion.close()
    return _trier_par_jour(lignes)


def _trier_par_jour(lignes):
    """Regroupe une liste de créneaux par jour (dans l'ordre Lundi -> Samedi), pour l'affichage."""
    par_jour = {jour: [] for jour in JOURS}
    for ligne in lignes:
        if ligne["jour"] in par_jour:
            par_jour[ligne["jour"]].append(ligne)
    return par_jour
