"""
utilisateurs.py
-----------------
Gère tout ce qui concerne les comptes utilisateurs : création,
authentification (vérification email + mot de passe), et rôles.

EDUVIA a 4 rôles :
    - prefet      : Préfet / Administrateur -> accès complet
    - enseignant  : gère les notes de ses classes (à venir)
    - eleve       : consulte ses propres informations (à venir)
    - parent      : consulte les informations de son/ses enfant(s) (à venir)

La connexion est gérée avec les sessions Flask (pas de bibliothèque
externe nécessaire) : voir decorateurs.py et app.py.
"""

from datetime import date
from werkzeug.security import generate_password_hash, check_password_hash

from database import obtenir_connexion

# Libellés affichés à l'écran pour chaque rôle
NOMS_ROLES = {
    "prefet": "Préfet / Administrateur",
    "enseignant": "Enseignant",
    "eleve": "Élève",
    "parent": "Parent / Tuteur",
    "secretariat": "Secrétariat",
}


class Utilisateur:
    """Représente un utilisateur connecté (version simple, sans dépendance externe)."""

    def __init__(self, ligne):
        self.id = ligne["id"]
        self.nom_complet = ligne["nom_complet"]
        self.email = ligne["email"]
        self.role = ligne["role"]
        self.actif = ligne["actif"]
        self.id_eleve = ligne["id_eleve"]  # rempli seulement si role == 'eleve'
        self.chemin_photo = ligne["chemin_photo"]
        self.is_authenticated = True  # utilisé dans les templates (ex: base.html)

    @property
    def nom_role(self):
        return NOMS_ROLES.get(self.role, self.role)


class UtilisateurAnonyme:
    """Représente un visiteur qui n'est pas connecté (évite les erreurs dans les templates)."""
    is_authenticated = False
    role = None
    nom_complet = ""
    nom_role = ""


def ajouter_utilisateur(nom_complet, email, mot_de_passe, role, id_eleve=None,
                         matricule_enseignant=None, specialite=None):
    """
    Crée un nouveau compte utilisateur avec mot de passe chiffré (haché).
    id_eleve : uniquement pour un compte de rôle 'eleve', relie le compte
    à sa fiche dans la table 'eleves' (voir models.py).
    matricule_enseignant/specialite : uniquement pour un compte de rôle 'enseignant'.
    """
    connexion = obtenir_connexion()
    curseur = connexion.execute("""
        INSERT INTO utilisateurs
            (nom_complet, email, mot_de_passe_hash, role, actif, id_eleve,
             matricule_enseignant, specialite, date_creation)
        VALUES (?, ?, ?, ?, 1, ?, ?, ?, ?)
    """, (
        nom_complet.strip(),
        email.strip().lower(),
        generate_password_hash(mot_de_passe),
        role,
        id_eleve,
        matricule_enseignant,
        specialite,
        date.today().isoformat(),
    ))
    id_nouvel_utilisateur = curseur.lastrowid
    connexion.commit()
    connexion.close()
    return id_nouvel_utilisateur


def obtenir_utilisateur_par_id(id_utilisateur):
    connexion = obtenir_connexion()
    ligne = connexion.execute(
        "SELECT * FROM utilisateurs WHERE id = ?", (id_utilisateur,)
    ).fetchone()
    connexion.close()
    return Utilisateur(ligne) if ligne else None


def obtenir_compte_par_id_eleve(id_eleve):
    """Retourne le compte utilisateur (brut, pas un objet Utilisateur) lié à une fiche élève, s'il existe."""
    connexion = obtenir_connexion()
    ligne = connexion.execute(
        "SELECT * FROM utilisateurs WHERE id_eleve = ?", (id_eleve,)
    ).fetchone()
    connexion.close()
    return ligne


def verifier_identifiants(email, mot_de_passe):
    """
    Vérifie l'email et le mot de passe fournis lors de la connexion.
    Retourne un Utilisateur si c'est correct et le compte est actif, sinon None.
    """
    connexion = obtenir_connexion()
    ligne = connexion.execute(
        "SELECT * FROM utilisateurs WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    connexion.close()

    if ligne is None or not ligne["actif"]:
        return None
    if not check_password_hash(ligne["mot_de_passe_hash"], mot_de_passe):
        return None
    return Utilisateur(ligne)


def lister_utilisateurs():
    connexion = obtenir_connexion()
    lignes = connexion.execute(
        "SELECT * FROM utilisateurs ORDER BY role, nom_complet"
    ).fetchall()
    connexion.close()
    return lignes


def verifier_mot_de_passe(id_utilisateur, mot_de_passe):
    """Vérifie qu'un mot de passe correspond bien à celui d'un utilisateur (pour confirmer avant de le changer)."""
    connexion = obtenir_connexion()
    ligne = connexion.execute("SELECT mot_de_passe_hash FROM utilisateurs WHERE id = ?", (id_utilisateur,)).fetchone()
    connexion.close()
    return ligne is not None and check_password_hash(ligne["mot_de_passe_hash"], mot_de_passe)


def changer_mot_de_passe(id_utilisateur, nouveau_mot_de_passe):
    connexion = obtenir_connexion()
    connexion.execute(
        "UPDATE utilisateurs SET mot_de_passe_hash = ? WHERE id = ?",
        (generate_password_hash(nouveau_mot_de_passe), id_utilisateur)
    )
    connexion.commit()
    connexion.close()


def mot_de_passe_est_celui_par_defaut(id_utilisateur):
    """Vrai si le compte utilise encore le mot de passe par défaut admin123 (pour avertir le Préfet)."""
    return verifier_mot_de_passe(id_utilisateur, "admin123")


def mettre_a_jour_photo(id_utilisateur, chemin_photo):
    connexion = obtenir_connexion()
    connexion.execute("UPDATE utilisateurs SET chemin_photo = ? WHERE id = ?", (chemin_photo, id_utilisateur))
    connexion.commit()
    connexion.close()


def email_existe(email):
    connexion = obtenir_connexion()
    ligne = connexion.execute(
        "SELECT id FROM utilisateurs WHERE email = ?", (email.strip().lower(),)
    ).fetchone()
    connexion.close()
    return ligne is not None


def basculer_statut_compte(id_utilisateur):
    """
    Active un compte désactivé, ou désactive un compte actif (inverse le statut).
    Retourne le nouvel état (True = actif, False = désactivé).
    Un compte désactivé ne peut plus se connecter (voir verifier_identifiants).
    """
    connexion = obtenir_connexion()
    ligne = connexion.execute(
        "SELECT actif FROM utilisateurs WHERE id = ?", (id_utilisateur,)
    ).fetchone()
    nouveau_statut = 0 if ligne["actif"] else 1
    connexion.execute(
        "UPDATE utilisateurs SET actif = ? WHERE id = ?", (nouveau_statut, id_utilisateur)
    )
    connexion.commit()
    connexion.close()
    return bool(nouveau_statut)


def creer_compte_admin_par_defaut():
    """
    Si aucun utilisateur n'existe encore (premier démarrage de l'application),
    crée un compte Préfet/Administrateur par défaut afin qu'il soit possible
    de se connecter au moins une fois.
    Le mot de passe DOIT être changé après la première connexion.
    """
    connexion = obtenir_connexion()
    total = connexion.execute("SELECT COUNT(*) AS total FROM utilisateurs").fetchone()["total"]
    connexion.close()

    if total == 0:
        ajouter_utilisateur(
            nom_complet="Administrateur EDUVIA",
            email="admin@eduvia.local",
            mot_de_passe="admin123",
            role="prefet",
        )
        print("=" * 60)
        print("Compte administrateur par défaut créé :")
        print("  Email        : admin@eduvia.local")
        print("  Mot de passe : admin123")
        print("  -> À changer immédiatement après la première connexion.")
        print("=" * 60)
