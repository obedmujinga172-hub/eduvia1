"""
messages.py
------------
Communications générales publiées par le Préfet à destination des
enseignants. Ce n'est PAS une messagerie : lecture seule pour les
enseignants, pas de réponse ni de commentaire.
"""

from datetime import datetime
from database import obtenir_connexion


def creer_message(titre, contenu, id_prefet):
    connexion = obtenir_connexion()
    connexion.execute("""
        INSERT INTO messages (titre, contenu, id_prefet, date_creation)
        VALUES (?, ?, ?, ?)
    """, (titre.strip(), contenu.strip(), id_prefet, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    connexion.commit()
    connexion.close()


def lister_messages():
    """Retourne tous les messages, du plus récent au plus ancien, avec le nom de l'auteur."""
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT messages.*, utilisateurs.nom_complet AS nom_auteur
        FROM messages
        JOIN utilisateurs ON utilisateurs.id = messages.id_prefet
        ORDER BY messages.id DESC
    """).fetchall()
    connexion.close()
    return lignes


def obtenir_message(id_message):
    connexion = obtenir_connexion()
    ligne = connexion.execute("SELECT * FROM messages WHERE id = ?", (id_message,)).fetchone()
    connexion.close()
    return ligne


def modifier_message(id_message, titre, contenu):
    connexion = obtenir_connexion()
    connexion.execute("""
        UPDATE messages SET titre = ?, contenu = ?, date_modification = ? WHERE id = ?
    """, (titre.strip(), contenu.strip(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"), id_message))
    connexion.commit()
    connexion.close()


def supprimer_message(id_message):
    connexion = obtenir_connexion()
    connexion.execute("DELETE FROM messages WHERE id = ?", (id_message,))
    connexion.commit()
    connexion.close()
