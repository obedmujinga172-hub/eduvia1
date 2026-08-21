"""
database.py
------------
Ce fichier s'occupe UNIQUEMENT de la connexion à la base de données
et de la création des tables (structure des données).

On utilise SQLite : la base de données est un simple fichier
(eduvia.db) qui sera créé automatiquement, sans rien installer.
"""

import sqlite3

NOM_BASE = "eduvia.db"


def obtenir_connexion():
    """
    Ouvre une connexion vers la base de données.
    row_factory permet de récupérer les résultats comme des dictionnaires
    (ex: eleve["nom"] au lieu de eleve[1]) -> plus lisible.
    """
    connexion = sqlite3.connect(NOM_BASE)
    connexion.row_factory = sqlite3.Row
    return connexion


def initialiser_base():
    """
    Crée les tables si elles n'existent pas encore.
    Cette fonction est appelée une seule fois, au démarrage de l'application.
    """
    connexion = obtenir_connexion()

    # ---------- ORGANISATION SCOLAIRE (configurée par le Préfet) ----------

    # Une année scolaire (ex: "2025-2026"). Une seule est "active" à la fois :
    # c'est celle utilisée par défaut pour les nouvelles inscriptions.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS annees_scolaires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            libelle TEXT UNIQUE NOT NULL,
            active INTEGER NOT NULL DEFAULT 0
        )
    """)

    # Une option/filière (ex: "Scientifique", "Commerciale", "Pédagogique").
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS options (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL,
            description TEXT
        )
    """)

    # Une classe concrète de l'école (ex: "3ème Scientifique A"), rattachée à
    # une année scolaire et, si besoin, à une option. L'école définit
    # elle-même ses classes : rien n'est codé en dur.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            niveau TEXT NOT NULL,
            nom TEXT NOT NULL,
            id_option INTEGER REFERENCES options(id),
            id_annee_scolaire INTEGER NOT NULL REFERENCES annees_scolaires(id),
            UNIQUE(nom, id_annee_scolaire)
        )
    """)

    # Une matière enseignée dans l'école (ex: "Mathématiques", "Français").
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS matieres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT UNIQUE NOT NULL,
            description TEXT
        )
    """)

    # ---------- ELEVES ----------
    # La classe de l'élève est maintenant un vrai lien vers la table
    # 'classes' (et plus un simple texte) : elle reflète l'organisation
    # réellement configurée par l'école.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS eleves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            matricule TEXT UNIQUE NOT NULL,
            nom TEXT NOT NULL,
            postnom TEXT,
            prenom TEXT,
            sexe TEXT NOT NULL,
            date_naissance TEXT,
            lieu_naissance TEXT,
            id_classe INTEGER REFERENCES classes(id),
            nom_parent TEXT,
            contact_parent TEXT,
            adresse TEXT,
            statut TEXT NOT NULL DEFAULT 'ACTIF'
                CHECK (statut IN ('ACTIF', 'TRANSFERE', 'DIPLOME', 'EXCLU', 'ARCHIVE', 'INACTIF')),
            chemin_photo TEXT,
            date_inscription TEXT NOT NULL
        )
    """)

    # Historique scolaire d'un élève : trace les événements marquants de son
    # parcours (changement de statut, transfert...), conservé même si
    # l'élève quitte l'école ou que son accès est désactivé.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS historique_eleve (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_eleve INTEGER NOT NULL REFERENCES eleves(id),
            evenement TEXT NOT NULL,
            details TEXT,
            date_heure TEXT NOT NULL
        )
    """)

    # ---------- UTILISATEURS ----------
    # Un utilisateur = une personne qui peut se connecter à EDUVIA.
    # Le rôle détermine ce qu'elle a le droit de faire (voir decorateurs.py).
    # matricule_enseignant/specialite ne concernent que les comptes enseignant.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS utilisateurs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom_complet TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            mot_de_passe_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('prefet', 'enseignant', 'eleve', 'parent', 'secretariat')),
            actif INTEGER NOT NULL DEFAULT 1,
            id_eleve INTEGER REFERENCES eleves(id),
            matricule_enseignant TEXT,
            specialite TEXT,
            chemin_photo TEXT,
            date_creation TEXT NOT NULL
        )
    """)

    # Journal d'audit : garde une trace des actions sensibles
    # (qui a fait quoi, et quand) pour la traçabilité administrative.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS journal_activites (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_utilisateur INTEGER,
            nom_utilisateur TEXT NOT NULL,
            action TEXT NOT NULL,
            details TEXT,
            date_heure TEXT NOT NULL
        )
    """)

    # Un parent peut être lié à plusieurs élèves (et un élève peut avoir
    # plusieurs parents/tuteurs enregistrés) : d'où une table à part,
    # plutôt qu'une simple colonne comme pour les comptes "élève".
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS parents_eleves (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_parent INTEGER NOT NULL REFERENCES utilisateurs(id),
            id_eleve INTEGER NOT NULL REFERENCES eleves(id),
            UNIQUE(id_parent, id_eleve)
        )
    """)

    # Attribution : quel enseignant a le droit d'enseigner (et donc de noter)
    # une matière donnée dans une classe donnée. C'est cette table qui
    # détermine les permissions réelles sur la saisie des notes.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS attributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_enseignant INTEGER NOT NULL REFERENCES utilisateurs(id),
            id_classe INTEGER NOT NULL REFERENCES classes(id),
            id_matiere INTEGER NOT NULL REFERENCES matieres(id),
            UNIQUE(id_enseignant, id_classe, id_matiere)
        )
    """)

    # Une note = le résultat d'un élève dans une matière, pour une période
    # donnée (trimestre). Une seule note par élève/matière/période dans
    # cette première version (pas encore de sous-évaluations multiples).
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_eleve INTEGER NOT NULL REFERENCES eleves(id),
            id_matiere INTEGER NOT NULL REFERENCES matieres(id),
            id_classe INTEGER NOT NULL REFERENCES classes(id),
            periode TEXT NOT NULL,
            valeur REAL NOT NULL,
            id_enseignant INTEGER REFERENCES utilisateurs(id),
            date_saisie TEXT NOT NULL,
            UNIQUE(id_eleve, id_matiere, periode)
        )
    """)

    # Une présence = le statut de présence d'un élève, pour une matière/classe/
    # enseignant donné, à une date précise. On enregistre par matière (et pas
    # seulement par jour) car chaque enseignant appelle sa propre liste.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS presences (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_eleve INTEGER NOT NULL REFERENCES eleves(id),
            id_classe INTEGER NOT NULL REFERENCES classes(id),
            id_matiere INTEGER REFERENCES matieres(id),
            id_enseignant INTEGER REFERENCES utilisateurs(id),
            date_jour TEXT NOT NULL,
            statut TEXT NOT NULL CHECK (statut IN ('PRESENT', 'ABSENT', 'RETARD')),
            date_saisie TEXT NOT NULL,
            UNIQUE(id_eleve, id_matiere, date_jour)
        )
    """)

    # Un créneau d'horaire s'appuie sur une attribution existante
    # (enseignant + classe + matière déjà validés), on y ajoute juste
    # le jour et l'heure. Cela évite d'avoir un enseignant "hors service"
    # dans l'emploi du temps d'une classe qu'il n'enseigne pas.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS horaires (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_attribution INTEGER NOT NULL REFERENCES attributions(id),
            jour TEXT NOT NULL,
            heure_debut TEXT NOT NULL,
            heure_fin TEXT NOT NULL
        )
    """)

    # Un frais scolaire = une ligne de coût attendue pour une classe donnée
    # (ex: "Minerval" 150000 CDF pour 3ème A). Le montant total attendu
    # pour un élève est la somme des frais configurés pour SA classe.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS frais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_classe INTEGER NOT NULL REFERENCES classes(id),
            nom TEXT NOT NULL,
            montant REAL NOT NULL,
            devise TEXT NOT NULL DEFAULT 'CDF' CHECK (devise IN ('CDF', 'USD'))
        )
    """)

    # Un paiement enregistré pour un élève (non lié à une ligne de frais
    # précise : dans la pratique congolaise, un parent paie souvent un
    # montant global, pas ligne par ligne).
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS paiements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_eleve INTEGER NOT NULL REFERENCES eleves(id),
            montant REAL NOT NULL,
            devise TEXT NOT NULL DEFAULT 'CDF' CHECK (devise IN ('CDF', 'USD')),
            motif TEXT,
            mode_paiement TEXT,
            reference TEXT,
            id_utilisateur INTEGER REFERENCES utilisateurs(id),
            date_paiement TEXT NOT NULL,
            date_saisie TEXT NOT NULL
        )
    """)

    # Paramètres de l'école : une seule ligne (id=1), utilisée pour
    # personnaliser les documents générés (bulletins, reçus...).
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS parametres_ecole (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nom_ecole TEXT NOT NULL DEFAULT 'EDUVIA',
            adresse TEXT,
            telephone TEXT,
            email TEXT,
            chemin_logo TEXT,
            chemin_cachet TEXT,
            nom_signataire TEXT,
            titre_signataire TEXT DEFAULT 'Le Préfet des études'
        )
    """)
    connexion.execute("INSERT OR IGNORE INTO parametres_ecole (id) VALUES (1)")

    # Règlement d'ordre intérieur : un seul fichier PDF, remplacé à chaque
    # nouvel import (pas d'historique de versions demandé ici — on reste simple).
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS reglement_interieur (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nom_fichier_original TEXT,
            date_import TEXT
        )
    """)
    connexion.execute("INSERT OR IGNORE INTO reglement_interieur (id) VALUES (1)")

    # Messages du Préfet vers les enseignants : communication à sens unique
    # (pas de réponse, pas de commentaire). Le Préfet est seul auteur.
    connexion.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            titre TEXT NOT NULL,
            contenu TEXT NOT NULL,
            id_prefet INTEGER NOT NULL REFERENCES utilisateurs(id),
            date_creation TEXT NOT NULL,
            date_modification TEXT
        )
    """)

    connexion.commit()
    connexion.close()
