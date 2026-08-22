"""
paiements.py
-------------
Gère :
  - les frais scolaires configurés par classe (montant attendu), chacun
    dans une devise précise : franc congolais (CDF) ou dollar américain (USD).
  - les paiements enregistrés pour un élève, chacun dans une devise.
  - le calcul automatique des soldes, SÉPARÉMENT par devise (on ne mélange
    jamais un montant CDF avec un montant USD).
"""

from datetime import date, datetime
from database import obtenir_connexion

MODES_PAIEMENT = ["Espèces", "Mobile Money", "Virement bancaire", "Chèque"]
DEVISES = ["CDF", "USD"]


# ================= FRAIS SCOLAIRES =================

def ajouter_frais(id_classe, nom, montant, devise):
    connexion = obtenir_connexion()
    connexion.execute("INSERT INTO frais (id_classe, nom, montant, devise) VALUES (?, ?, ?, ?)",
                       (id_classe, nom.strip(), montant, devise))
    connexion.commit()
    connexion.close()


def lister_frais_classe(id_classe):
    connexion = obtenir_connexion()
    lignes = connexion.execute("SELECT * FROM frais WHERE id_classe = ? ORDER BY devise, nom", (id_classe,)).fetchall()
    connexion.close()
    return lignes


def supprimer_frais(id_frais):
    connexion = obtenir_connexion()
    connexion.execute("DELETE FROM frais WHERE id = ?", (id_frais,))
    connexion.commit()
    connexion.close()


def montant_attendu_classe(id_classe):
    """Retourne {'CDF': total, 'USD': total} : la somme des frais configurés pour une classe, par devise."""
    connexion = obtenir_connexion()
    lignes = connexion.execute(
        "SELECT devise, COALESCE(SUM(montant), 0) AS total FROM frais WHERE id_classe = ? GROUP BY devise",
        (id_classe,)
    ).fetchall()
    connexion.close()
    totaux = {devise: 0.0 for devise in DEVISES}
    for ligne in lignes:
        totaux[ligne["devise"]] = ligne["total"]
    return totaux


# ================= PAIEMENTS =================

def enregistrer_paiement(id_eleve, montant, devise, motif, mode_paiement, reference, id_utilisateur, date_paiement=None):
    connexion = obtenir_connexion()
    curseur = connexion.execute("""
        INSERT INTO paiements (id_eleve, montant, devise, motif, mode_paiement, reference, id_utilisateur, date_paiement, date_saisie)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        id_eleve, montant, devise, motif, mode_paiement, reference, id_utilisateur,
        date_paiement or date.today().isoformat(),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ))
    id_paiement = curseur.lastrowid
    connexion.commit()
    connexion.close()
    return id_paiement


def obtenir_paiement(id_paiement):
    connexion = obtenir_connexion()
    ligne = connexion.execute("SELECT * FROM paiements WHERE id = ?", (id_paiement,)).fetchone()
    connexion.close()
    return ligne


def obtenir_historique_paiements(id_eleve):
    connexion = obtenir_connexion()
    lignes = connexion.execute("""
        SELECT * FROM paiements WHERE id_eleve = ? ORDER BY date_paiement DESC, id DESC
    """, (id_eleve,)).fetchall()
    connexion.close()
    return lignes


def montant_paye(id_eleve):
    """Retourne {'CDF': total, 'USD': total} déjà payé par l'élève, par devise."""
    connexion = obtenir_connexion()
    lignes = connexion.execute(
        "SELECT devise, COALESCE(SUM(montant), 0) AS total FROM paiements WHERE id_eleve = ? GROUP BY devise",
        (id_eleve,)
    ).fetchall()
    connexion.close()
    totaux = {devise: 0.0 for devise in DEVISES}
    for ligne in lignes:
        totaux[ligne["devise"]] = ligne["total"]
    return totaux


def calculer_soldes(id_eleve, id_classe):
    """
    Retourne, pour chaque devise (CDF et USD séparément) :
        {"CDF": {"attendu": .., "paye": .., "solde": ..}, "USD": {...}}
    Calculé automatiquement à partir des frais de la classe et des paiements enregistrés.
    Les deux devises ne sont JAMAIS additionnées ensemble.
    """
    attendu_par_devise = montant_attendu_classe(id_classe) if id_classe else {d: 0.0 for d in DEVISES}
    paye_par_devise = montant_paye(id_eleve)
    return {
        devise: {
            "attendu": attendu_par_devise[devise],
            "paye": paye_par_devise[devise],
            "solde": attendu_par_devise[devise] - paye_par_devise[devise],
        }
        for devise in DEVISES
    }
