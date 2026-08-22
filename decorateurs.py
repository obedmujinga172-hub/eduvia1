"""
decorateurs.py
----------------
Contient les décorateurs qui protègent les routes :

  @connexion_requise        -> il faut être connecté
  @role_requis("prefet")    -> il faut être connecté ET avoir le bon rôle

IMPORTANT : ce contrôle se fait CÔTÉ SERVEUR (dans le code Python),
pas seulement en cachant des boutons dans les templates. Même si
quelqu'un connaît directement l'adresse d'une page, il sera bloqué
ici s'il n'a pas le bon rôle.
"""

from functools import wraps
from flask import session, redirect, url_for, abort, g

import utilisateurs


def utilisateur_courant():
    """
    Retourne l'utilisateur actuellement connecté (à partir de la session),
    ou un UtilisateurAnonyme si personne n'est connecté OU si son compte
    vient d'être désactivé entretemps (vérifié à chaque requête, pas
    seulement à la connexion : la désactivation doit être immédiate).
    Le résultat est mis en cache dans 'g' pour ne lire la base qu'une fois par requête.
    """
    if "utilisateur" not in g:
        id_utilisateur = session.get("id_utilisateur")
        if id_utilisateur is None:
            g.utilisateur = utilisateurs.UtilisateurAnonyme()
        else:
            utilisateur = utilisateurs.obtenir_utilisateur_par_id(id_utilisateur)
            if utilisateur is None or not utilisateur.actif:
                # Compte supprimé ou désactivé depuis la connexion :
                # on invalide la session immédiatement.
                session.pop("id_utilisateur", None)
                g.utilisateur = utilisateurs.UtilisateurAnonyme()
            else:
                g.utilisateur = utilisateur
    return g.utilisateur


def connexion_requise(fonction_route):
    """Bloque l'accès si personne n'est connecté, et renvoie vers la page de connexion."""
    @wraps(fonction_route)
    def fonction_protegee(*args, **kwargs):
        if not utilisateur_courant().is_authenticated:
            return redirect(url_for("connexion"))
        return fonction_route(*args, **kwargs)
    return fonction_protegee


def role_requis(*roles_autorises):
    """
    Décorateur paramétrable : role_requis("prefet", "enseignant")
    autorise seulement les utilisateurs ayant l'un de ces rôles.
    Doit être placé APRÈS @connexion_requise.
    Les rôles non autorisés reçoivent une erreur 403 (accès refusé).
    """
    def decorateur(fonction_route):
        @wraps(fonction_route)
        def fonction_protegee(*args, **kwargs):
            if not utilisateur_courant().is_authenticated:
                return redirect(url_for("connexion"))
            if utilisateur_courant().role not in roles_autorises:
                abort(403)
            return fonction_route(*args, **kwargs)
        return fonction_protegee
    return decorateur
