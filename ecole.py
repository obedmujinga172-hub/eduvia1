"""
ecole.py
---------
Gère les paramètres personnalisables de l'école, utilisés pour habiller
les documents générés (bulletins PDF, reçus...) : nom, coordonnées, logo,
cachet, signature. Une seule ligne en base (id=1).
"""

from database import obtenir_connexion


def obtenir_parametres():
    connexion = obtenir_connexion()
    ligne = connexion.execute("SELECT * FROM parametres_ecole WHERE id = 1").fetchone()
    connexion.close()
    return ligne


def mettre_a_jour_parametres(nom_ecole, adresse, telephone, email, nom_signataire, titre_signataire):
    connexion = obtenir_connexion()
    connexion.execute("""
        UPDATE parametres_ecole SET
            nom_ecole = ?, adresse = ?, telephone = ?, email = ?,
            nom_signataire = ?, titre_signataire = ?
        WHERE id = 1
    """, (nom_ecole.strip(), adresse.strip(), telephone.strip(), email.strip(),
          nom_signataire.strip(), titre_signataire.strip()))
    connexion.commit()
    connexion.close()


def mettre_a_jour_logo(chemin_logo):
    connexion = obtenir_connexion()
    connexion.execute("UPDATE parametres_ecole SET chemin_logo = ? WHERE id = 1", (chemin_logo,))
    connexion.commit()
    connexion.close()


def mettre_a_jour_cachet(chemin_cachet):
    connexion = obtenir_connexion()
    connexion.execute("UPDATE parametres_ecole SET chemin_cachet = ? WHERE id = 1", (chemin_cachet,))
    connexion.commit()
    connexion.close()
