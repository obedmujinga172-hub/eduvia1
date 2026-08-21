"""
app.py
-------
Point d'entrée de l'application EDUVIA.
Contient les routes (pages) ainsi que la gestion de la connexion
et des permissions par rôle.

Pour lancer l'application :
    python app.py
Puis ouvrir dans un navigateur : http://127.0.0.1:5000
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, send_file, abort
import os
import tempfile
from datetime import date

from database import initialiser_base
import models
import utilisateurs
import audit
import parents
import organisation
import notes as module_notes
import presences
import horaires
import paiements
import bulletin
import recu
import ecole
import reglement
import messages as module_messages
import photos
from utilisateurs import NOMS_ROLES
from decorateurs import connexion_requise, role_requis, utilisateur_courant

app = Flask(__name__, templates_folder='.'

# SÉCURITÉ : en production, la clé secrète DOIT être définie via la variable
# d'environnement EDUVIA_SECRET_KEY (une longue chaîne aléatoire, différente
# pour chaque installation). Sans ça, quiconque lit le code source pourrait
# forger de fausses sessions de connexion. La valeur ci-dessous n'est qu'un
# filet de sécurité pour le développement local.
app.secret_key = os.environ.get("EDUVIA_SECRET_KEY", "cle-secrete-a-changer-plus-tard-DEV-UNIQUEMENT")

# SÉCURITÉ : ces réglages protègent le cookie de session. SESSION_COOKIE_SECURE
# n'a d'effet que si le site est servi en HTTPS (ce qui doit être le cas dès
# que l'application est accessible sur internet).
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = os.environ.get("EDUVIA_HTTPS", "0") == "1"

# ---------- Préparation de la base de données ----------
initialiser_base()
utilisateurs.creer_compte_admin_par_defaut()


@app.context_processor
def injecter_utilisateur_courant():
    """
    Rend la variable 'current_user' disponible dans TOUS les templates
    (base.html, accueil.html, etc.) sans avoir à la passer à chaque render_template.
    """
    return {"current_user": utilisateur_courant()}


# ---------- CONNEXION / DÉCONNEXION ----------

@app.route("/connexion", methods=["GET", "POST"])
def connexion():
    if utilisateur_courant().is_authenticated:
        return redirect(url_for("accueil"))

    if request.method == "POST":
        email = request.form["email"]
        mot_de_passe = request.form["mot_de_passe"]
        utilisateur = utilisateurs.verifier_identifiants(email, mot_de_passe)

        if utilisateur is None:
            flash("Email ou mot de passe incorrect.", "erreur")
            return render_template("connexion.html")

        session["id_utilisateur"] = utilisateur.id
        audit.enregistrer(utilisateur, "Connexion")
        return redirect(url_for("accueil"))

    return render_template("connexion.html")


@app.route("/deconnexion")
@connexion_requise
def deconnexion():
    session.clear()
    flash("Vous avez été déconnecté.", "succes")
    return redirect(url_for("connexion"))


# ---------- GESTION DES ERREURS D'ACCÈS ----------

@app.errorhandler(403)
def acces_refuse(erreur):
    return render_template("erreur.html",
                            code=403,
                            message="Vous n'avez pas la permission d'accéder à cette page."), 403


# ---------- PAGE D'ACCUEIL ----------

@app.route("/")
@connexion_requise
def accueil():
    utilisateur = utilisateur_courant()
    total_eleves = models.compter_eleves() if utilisateur.role in ("prefet", "enseignant") else None
    return render_template("accueil.html", total_eleves=total_eleves)


@app.route("/service-worker.js")
def service_worker():
    """Sert le service worker à la racine pour lui donner toute l'application comme portée."""
    reponse = send_file(
        os.path.join(app.static_folder, "service-worker.js"),
        mimetype="application/javascript",
    )
    reponse.headers["Cache-Control"] = "no-cache"
    return reponse


# ---------- PROFIL (tous les rôles connectés) ----------

@app.route("/profil")
@connexion_requise
def profil():
    utilisateur = utilisateur_courant()
    eleve = None
    enfants = None
    notes_par_periode = {}

    if utilisateur.role == "eleve" and utilisateur.id_eleve:
        eleve = models.obtenir_eleve_par_id(utilisateur.id_eleve)
        if eleve:
            for periode in module_notes.PERIODES:
                notes_par_periode[periode] = {
                    "notes": module_notes.obtenir_notes_eleve(eleve["id"], periode),
                    "moyenne": module_notes.calculer_moyenne(eleve["id"], periode),
                }
    elif utilisateur.role == "parent":
        enfants = parents.obtenir_enfants(utilisateur.id)

    soldes_enfants = None
    solde_eleve = None
    if eleve:
        solde_eleve = paiements.calculer_soldes(eleve["id"], eleve["id_classe"])
    if enfants is not None:
        soldes_enfants = {enfant["id"]: paiements.calculer_soldes(enfant["id"], enfant["id_classe"]) for enfant in enfants}

    mot_de_passe_par_defaut = (
        utilisateur.role == "prefet" and utilisateurs.mot_de_passe_est_celui_par_defaut(utilisateur.id)
    )

    return render_template("profil.html", eleve=eleve, enfants=enfants,
                            notes_par_periode=notes_par_periode, periodes=module_notes.PERIODES,
                            solde_eleve=solde_eleve, soldes_enfants=soldes_enfants,
                            mot_de_passe_par_defaut=mot_de_passe_par_defaut)


@app.route("/profil/mot-de-passe", methods=["GET", "POST"])
@connexion_requise
def changer_mot_de_passe():
    utilisateur = utilisateur_courant()

    if request.method == "POST":
        mot_de_passe_actuel = request.form["mot_de_passe_actuel"]
        nouveau = request.form["nouveau_mot_de_passe"]
        confirmation = request.form["confirmation"]

        if not utilisateurs.verifier_mot_de_passe(utilisateur.id, mot_de_passe_actuel):
            flash("Le mot de passe actuel est incorrect.", "erreur")
            return render_template("changer_mot_de_passe.html")

        if len(nouveau) < 6:
            flash("Le nouveau mot de passe doit contenir au moins 6 caractères.", "erreur")
            return render_template("changer_mot_de_passe.html")

        if nouveau != confirmation:
            flash("Les deux mots de passe ne correspondent pas.", "erreur")
            return render_template("changer_mot_de_passe.html")

        utilisateurs.changer_mot_de_passe(utilisateur.id, nouveau)
        audit.enregistrer(utilisateur, "Changement de mot de passe")
        flash("Mot de passe changé avec succès.", "succes")
        return redirect(url_for("profil"))

    return render_template("changer_mot_de_passe.html")


# ---------- LISTE DES ELEVES (Préfet + Enseignant) ----------

@app.route("/eleves")
@connexion_requise
@role_requis("prefet", "enseignant")
def liste_eleves():
    utilisateur = utilisateur_courant()
    recherche = request.args.get("recherche", "").strip()
    eleves = models.obtenir_tous_les_eleves(recherche if recherche else None)

    # Un enseignant ne doit voir que les élèves des classes qui lui sont
    # réellement attribuées (voir prompt 9), pas l'école entière.
    if utilisateur.role == "enseignant":
        classes_autorisees = {a["id_classe"] for a in module_notes.lister_attributions_enseignant(utilisateur.id)}
        eleves = [e for e in eleves if e["id_classe"] in classes_autorisees]

    return render_template("eleves/liste.html", eleves=eleves, recherche=recherche)


# ---------- AJOUTER UN ELEVE (Préfet uniquement) ----------

@app.route("/eleves/ajouter", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def ajouter_eleve():
    if request.method == "POST":
        donnees = {
            "matricule": request.form["matricule"].strip(),
            "nom": request.form["nom"].strip(),
            "postnom": request.form["postnom"].strip(),
            "prenom": request.form["prenom"].strip(),
            "sexe": request.form["sexe"],
            "date_naissance": request.form["date_naissance"],
            "lieu_naissance": request.form["lieu_naissance"].strip(),
            "id_classe": request.form.get("id_classe") or None,
            "nom_parent": request.form["nom_parent"].strip(),
            "contact_parent": request.form["contact_parent"].strip(),
            "adresse": request.form["adresse"].strip(),
        }
        id_nouvel_eleve = models.ajouter_eleve(donnees)

        chemin_photo = photos.enregistrer_photo(
            request.files.get("photo"), os.path.join("static", "photos", "eleves"), str(id_nouvel_eleve)
        )
        if request.files.get("photo") and request.files.get("photo").filename and not chemin_photo:
            flash("La photo n'a pas pu être enregistrée (fichier image invalide) ; l'élève a tout de même été ajouté.", "erreur")
        elif chemin_photo:
            models.mettre_a_jour_photo_eleve(id_nouvel_eleve, chemin_photo)

        audit.enregistrer(utilisateur_courant(), "Ajout d'un élève",
                           f"{donnees['prenom']} {donnees['nom']} (matricule {donnees['matricule']})")
        flash(f"L'élève {donnees['prenom']} {donnees['nom']} a été ajouté avec succès.", "succes")
        return redirect(url_for("liste_eleves"))

    return render_template("eleves/ajouter.html", classes=organisation.lister_classes())


# ---------- MODIFIER UN ELEVE (Préfet uniquement) ----------

@app.route("/eleves/modifier/<int:id_eleve>", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def modifier_eleve(id_eleve):
    eleve = models.obtenir_eleve_par_id(id_eleve)
    if eleve is None:
        flash("Élève introuvable.", "erreur")
        return redirect(url_for("liste_eleves"))

    if request.method == "POST":
        donnees = {
            "matricule": request.form["matricule"].strip(),
            "nom": request.form["nom"].strip(),
            "postnom": request.form["postnom"].strip(),
            "prenom": request.form["prenom"].strip(),
            "sexe": request.form["sexe"],
            "date_naissance": request.form["date_naissance"],
            "lieu_naissance": request.form["lieu_naissance"].strip(),
            "id_classe": request.form.get("id_classe") or None,
            "nom_parent": request.form["nom_parent"].strip(),
            "contact_parent": request.form["contact_parent"].strip(),
            "adresse": request.form["adresse"].strip(),
        }
        models.modifier_eleve(id_eleve, donnees)

        chemin_photo = photos.enregistrer_photo(
            request.files.get("photo"), os.path.join("static", "photos", "eleves"), str(id_eleve)
        )
        if request.files.get("photo") and request.files.get("photo").filename and not chemin_photo:
            flash("La photo n'a pas pu être enregistrée (fichier image invalide).", "erreur")
        elif chemin_photo:
            models.mettre_a_jour_photo_eleve(id_eleve, chemin_photo)

        audit.enregistrer(utilisateur_courant(), "Modification d'un élève",
                           f"{donnees['prenom']} {donnees['nom']} (matricule {donnees['matricule']})")
        flash("Les informations de l'élève ont été mises à jour.", "succes")
        return redirect(url_for("liste_eleves"))

    return render_template("eleves/modifier.html", eleve=eleve, classes=organisation.lister_classes())


# ---------- DOSSIER D'UN ELEVE (Préfet + Enseignant en lecture) ----------

@app.route("/eleves/<int:id_eleve>/dossier")
@connexion_requise
@role_requis("prefet", "enseignant")
def dossier_eleve(id_eleve):
    eleve = models.obtenir_eleve_par_id(id_eleve)
    if eleve is None:
        flash("Élève introuvable.", "erreur")
        return redirect(url_for("liste_eleves"))

    utilisateur = utilisateur_courant()
    # Un enseignant ne peut consulter que le dossier d'un élève d'une
    # classe où il enseigne réellement (voir attributions, prompt 9).
    if utilisateur.role == "enseignant":
        if not eleve["id_classe"] or not module_notes.enseignant_a_classe(utilisateur.id, eleve["id_classe"]):
            abort(403)

    historique = models.obtenir_historique_eleve(id_eleve)
    total_absences, total_retards = presences.compter_absences_retards(id_eleve)
    soldes = paiements.calculer_soldes(id_eleve, eleve["id_classe"])
    return render_template("eleves/dossier.html", eleve=eleve, historique=historique,
                            noms_statuts=models.NOMS_STATUTS,
                            total_absences=total_absences, total_retards=total_retards,
                            soldes=soldes)


@app.route("/eleves/<int:id_eleve>/statut", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def changer_statut_eleve(id_eleve):
    eleve = models.obtenir_eleve_par_id(id_eleve)
    if eleve is None:
        flash("Élève introuvable.", "erreur")
        return redirect(url_for("liste_eleves"))

    nouveau_statut = request.form["statut"]
    ancien_statut = eleve["statut"]
    note = request.form.get("note", "").strip()

    models.changer_statut_eleve(id_eleve, nouveau_statut)
    models.ajouter_evenement_historique(
        id_eleve,
        f"Changement de statut : {models.NOMS_STATUTS[ancien_statut]} → {models.NOMS_STATUTS[nouveau_statut]}",
        note,
    )
    audit.enregistrer(utilisateur_courant(), "Changement de statut d'un élève",
                       f"{eleve['prenom']} {eleve['nom']} : {ancien_statut} → {nouveau_statut}")

    message_supplementaire = ""
    # Quand un élève quitte l'école (tout statut autre qu'ACTIF), son
    # historique reste conservé, mais son accès à EDUVIA (s'il a un compte)
    # est désactivé automatiquement pour plus de sécurité.
    if nouveau_statut != "ACTIF":
        compte_lie = utilisateurs.obtenir_compte_par_id_eleve(id_eleve)
        if compte_lie and compte_lie["actif"]:
            utilisateurs.basculer_statut_compte(compte_lie["id"])
            audit.enregistrer(utilisateur_courant(), "Compte désactivé (élève ayant quitté l'école)",
                               f"{eleve['prenom']} {eleve['nom']}")
            message_supplementaire = " Son compte de connexion a été désactivé automatiquement."

    flash(f"Statut mis à jour : {models.NOMS_STATUTS[nouveau_statut]}.{message_supplementaire}", "succes")
    return redirect(url_for("dossier_eleve", id_eleve=id_eleve))


# ---------- SUPPRIMER UN ELEVE (Préfet uniquement) ----------

@app.route("/eleves/supprimer/<int:id_eleve>", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def supprimer_eleve(id_eleve):
    eleve = models.obtenir_eleve_par_id(id_eleve)
    models.supprimer_eleve(id_eleve)
    if eleve:
        audit.enregistrer(utilisateur_courant(), "Suppression d'un élève",
                           f"{eleve['prenom']} {eleve['nom']} (matricule {eleve['matricule']})")
    flash("L'élève a été supprimé.", "succes")
    return redirect(url_for("liste_eleves"))


# ---------- ANNEES SCOLAIRES (Préfet uniquement) ----------

@app.route("/annees-scolaires", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def liste_annees_scolaires():
    if request.method == "POST":
        libelle = request.form["libelle"].strip()
        organisation.ajouter_annee_scolaire(libelle)
        audit.enregistrer(utilisateur_courant(), "Ajout d'une année scolaire", libelle)
        flash(f"Année scolaire {libelle} créée.", "succes")
        return redirect(url_for("liste_annees_scolaires"))

    return render_template("organisation/annees_scolaires.html", annees=organisation.lister_annees_scolaires())


@app.route("/annees-scolaires/<int:id_annee>/activer", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def activer_annee_scolaire(id_annee):
    organisation.activer_annee_scolaire(id_annee)
    audit.enregistrer(utilisateur_courant(), "Activation d'une année scolaire", f"id {id_annee}")
    flash("Année scolaire activée.", "succes")
    return redirect(url_for("liste_annees_scolaires"))


# ---------- OPTIONS (Préfet uniquement) ----------

@app.route("/options", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def liste_options():
    if request.method == "POST":
        nom = request.form["nom"].strip()
        organisation.ajouter_option(nom, request.form.get("description", "").strip())
        audit.enregistrer(utilisateur_courant(), "Ajout d'une option", nom)
        flash(f"Option {nom} créée.", "succes")
        return redirect(url_for("liste_options"))

    return render_template("organisation/options.html", options=organisation.lister_options())


@app.route("/options/<int:id_option>/supprimer", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def supprimer_option(id_option):
    organisation.supprimer_option(id_option)
    audit.enregistrer(utilisateur_courant(), "Suppression d'une option", f"id {id_option}")
    flash("Option supprimée.", "succes")
    return redirect(url_for("liste_options"))


# ---------- CLASSES (Préfet uniquement) ----------

@app.route("/classes", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def liste_classes():
    if request.method == "POST":
        annee_active = organisation.obtenir_annee_active()
        if annee_active is None:
            flash("Veuillez d'abord créer et activer une année scolaire.", "erreur")
            return redirect(url_for("liste_classes"))

        organisation.ajouter_classe(
            niveau=request.form["niveau"],
            nom=request.form["nom"],
            id_option=request.form.get("id_option") or None,
            id_annee_scolaire=annee_active["id"],
        )
        audit.enregistrer(utilisateur_courant(), "Ajout d'une classe", request.form["nom"].strip())
        flash("Classe créée.", "succes")
        return redirect(url_for("liste_classes"))

    return render_template(
        "organisation/classes.html",
        classes=organisation.lister_classes(),
        options=organisation.lister_options(),
        niveaux=organisation.NIVEAUX_SECONDAIRE,
        annee_active=organisation.obtenir_annee_active(),
    )


@app.route("/classes/<int:id_classe>/supprimer", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def supprimer_classe(id_classe):
    organisation.supprimer_classe(id_classe)
    audit.enregistrer(utilisateur_courant(), "Suppression d'une classe", f"id {id_classe}")
    flash("Classe supprimée.", "succes")
    return redirect(url_for("liste_classes"))


# ---------- MATIERES (Préfet uniquement) ----------

@app.route("/matieres", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def liste_matieres():
    if request.method == "POST":
        nom = request.form["nom"].strip()
        organisation.ajouter_matiere(nom, request.form.get("description", "").strip())
        audit.enregistrer(utilisateur_courant(), "Ajout d'une matière", nom)
        flash(f"Matière {nom} créée.", "succes")
        return redirect(url_for("liste_matieres"))

    return render_template("organisation/matieres.html", matieres=organisation.lister_matieres())


@app.route("/matieres/<int:id_matiere>/supprimer", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def supprimer_matiere(id_matiere):
    organisation.supprimer_matiere(id_matiere)
    audit.enregistrer(utilisateur_courant(), "Suppression d'une matière", f"id {id_matiere}")
    flash("Matière supprimée.", "succes")
    return redirect(url_for("liste_matieres"))


# ---------- ATTRIBUTIONS (Préfet uniquement) ----------

@app.route("/attributions", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def liste_attributions():
    if request.method == "POST":
        module_notes.attribuer(
            id_enseignant=int(request.form["id_enseignant"]),
            id_classe=int(request.form["id_classe"]),
            id_matiere=int(request.form["id_matiere"]),
        )
        audit.enregistrer(utilisateur_courant(), "Attribution enseignant/classe/matière",
                           f"enseignant {request.form['id_enseignant']}")
        flash("Attribution enregistrée.", "succes")
        return redirect(url_for("liste_attributions"))

    tous_les_comptes = utilisateurs.lister_utilisateurs()
    enseignants = [c for c in tous_les_comptes if c["role"] == "enseignant"]
    return render_template("notes/attributions.html",
                            attributions=module_notes.lister_toutes_attributions(),
                            enseignants=enseignants,
                            classes=organisation.lister_classes(),
                            matieres=organisation.lister_matieres())


@app.route("/attributions/<int:id_attribution>/supprimer", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def supprimer_attribution(id_attribution):
    module_notes.supprimer_attribution(id_attribution)
    audit.enregistrer(utilisateur_courant(), "Suppression d'une attribution", f"id {id_attribution}")
    flash("Attribution supprimée.", "succes")
    return redirect(url_for("liste_attributions"))


# ---------- SAISIE DES NOTES (Enseignant : ses classes/matières / Préfet : toutes) ----------

@app.route("/notes/saisir", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet", "enseignant")
def saisir_notes():
    utilisateur = utilisateur_courant()

    if utilisateur.role == "enseignant":
        attributions_autorisees = module_notes.lister_attributions_enseignant(utilisateur.id)
    else:
        attributions_autorisees = module_notes.lister_toutes_attributions()

    if request.method == "POST":
        id_classe = int(request.form["id_classe"])
        id_matiere = int(request.form["id_matiere"])
        periode = request.form["periode"]

        # Vérification côté serveur : un enseignant ne peut saisir QUE
        # dans une classe/matière qui lui a été attribuée.
        if utilisateur.role == "enseignant" and not module_notes.enseignant_a_droit(utilisateur.id, id_classe, id_matiere):
            flash("Vous n'êtes pas autorisé à saisir des notes pour cette classe/matière.", "erreur")
            return redirect(url_for("saisir_notes"))

        for cle, valeur in request.form.items():
            if cle.startswith("note_") and valeur.strip() != "":
                id_eleve = int(cle.replace("note_", ""))
                try:
                    valeur_note = float(valeur)
                except ValueError:
                    continue
                if 0 <= valeur_note <= 20:
                    module_notes.enregistrer_note(id_eleve, id_matiere, id_classe, periode, valeur_note, utilisateur.id)

        audit.enregistrer(utilisateur, "Saisie de notes",
                           f"classe {id_classe}, matière {id_matiere}, période {periode}")
        flash("Notes enregistrées avec succès.", "succes")
        return redirect(url_for("saisir_notes", id_classe=id_classe, id_matiere=id_matiere, periode=periode))

    id_classe = request.args.get("id_classe", type=int)
    id_matiere = request.args.get("id_matiere", type=int)
    periode = request.args.get("periode")
    eleves_notes = None

    if id_classe and id_matiere and periode:
        if utilisateur.role == "enseignant" and not module_notes.enseignant_a_droit(utilisateur.id, id_classe, id_matiere):
            flash("Vous n'êtes pas autorisé à saisir des notes pour cette classe/matière.", "erreur")
            return redirect(url_for("saisir_notes"))
        eleves_notes = module_notes.obtenir_notes_classe_matiere(id_classe, id_matiere, periode)

    return render_template("notes/saisir.html",
                            attributions=attributions_autorisees,
                            periodes=module_notes.PERIODES,
                            id_classe=id_classe, id_matiere=id_matiere, periode=periode,
                            eleves_notes=eleves_notes)


# ---------- RESULTATS DE CLASSE (Préfet : toutes / Enseignant : ses classes) ----------

@app.route("/notes/resultats")
@connexion_requise
@role_requis("prefet", "enseignant")
def resultats_classe():
    utilisateur = utilisateur_courant()

    if utilisateur.role == "enseignant":
        classes_autorisees = {a["id_classe"] for a in module_notes.lister_attributions_enseignant(utilisateur.id)}
        classes = [c for c in organisation.lister_classes() if c["id"] in classes_autorisees]
    else:
        classes = organisation.lister_classes()

    id_classe = request.args.get("id_classe", type=int)
    periode = request.args.get("periode", module_notes.PERIODES[0])
    resultats = None

    if id_classe:
        if utilisateur.role == "enseignant" and id_classe not in classes_autorisees:
            flash("Vous n'avez pas accès aux résultats de cette classe.", "erreur")
            return redirect(url_for("resultats_classe"))
        resultats = module_notes.obtenir_resultats_classe(id_classe, periode)

    return render_template("notes/resultats.html", classes=classes, periodes=module_notes.PERIODES,
                            id_classe=id_classe, periode=periode, resultats=resultats)


# ---------- BULLETIN PDF ----------

@app.route("/eleves/<int:id_eleve>/bulletin/<periode>")
@connexion_requise
def telecharger_bulletin(id_eleve, periode):
    utilisateur = utilisateur_courant()
    eleve = models.obtenir_eleve_par_id(id_eleve)
    if eleve is None:
        flash("Élève introuvable.", "erreur")
        return redirect(url_for("accueil"))

    # Contrôle d'accès : chacun ne peut télécharger que ce qui le concerne.
    autorise = False
    if utilisateur.role == "prefet":
        autorise = True
    elif utilisateur.role == "enseignant":
        autorise = eleve["id_classe"] and module_notes.enseignant_a_classe(utilisateur.id, eleve["id_classe"])
    elif utilisateur.role == "eleve":
        autorise = utilisateur.id_eleve == id_eleve
    elif utilisateur.role == "parent":
        autorise = parents.parent_est_lie_a_eleve(utilisateur.id, id_eleve)

    if not autorise:
        abort(403)

    chemin_temporaire = os.path.join(tempfile.gettempdir(), f"bulletin_{id_eleve}_{periode.replace(' ', '_')}.pdf")
    bulletin.generer_bulletin_pdf(eleve, periode, chemin_temporaire)

    audit.enregistrer(utilisateur, "Génération d'un bulletin",
                       f"{eleve['prenom']} {eleve['nom']} - {periode}")

    nom_fichier = f"Bulletin_{eleve['nom']}_{eleve['prenom']}_{periode.replace(' ', '_')}.pdf"
    return send_file(chemin_temporaire, as_attachment=True, download_name=nom_fichier)


# ---------- SAISIE DES PRESENCES (Enseignant : ses classes/matières / Préfet : toutes) ----------

@app.route("/presences/saisir", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet", "enseignant")
def saisir_presences():
    utilisateur = utilisateur_courant()

    if utilisateur.role == "enseignant":
        attributions_autorisees = module_notes.lister_attributions_enseignant(utilisateur.id)
    else:
        attributions_autorisees = module_notes.lister_toutes_attributions()

    if request.method == "POST":
        id_classe = int(request.form["id_classe"])
        id_matiere = int(request.form["id_matiere"])
        date_jour = request.form["date_jour"]

        if utilisateur.role == "enseignant" and not module_notes.enseignant_a_droit(utilisateur.id, id_classe, id_matiere):
            flash("Vous n'êtes pas autorisé à saisir des présences pour cette classe/matière.", "erreur")
            return redirect(url_for("saisir_presences"))

        for cle, valeur in request.form.items():
            if cle.startswith("statut_") and valeur in ("PRESENT", "ABSENT", "RETARD"):
                id_eleve = int(cle.replace("statut_", ""))
                presences.enregistrer_presence(id_eleve, id_classe, id_matiere, utilisateur.id, date_jour, valeur)

        audit.enregistrer(utilisateur, "Saisie de présences",
                           f"classe {id_classe}, matière {id_matiere}, date {date_jour}")
        flash("Présences enregistrées avec succès.", "succes")
        return redirect(url_for("saisir_presences", id_classe=id_classe, id_matiere=id_matiere, date_jour=date_jour))

    id_classe = request.args.get("id_classe", type=int)
    id_matiere = request.args.get("id_matiere", type=int)
    date_jour = request.args.get("date_jour") or date.today().isoformat()
    eleves_presences = None

    if id_classe and id_matiere:
        if utilisateur.role == "enseignant" and not module_notes.enseignant_a_droit(utilisateur.id, id_classe, id_matiere):
            flash("Vous n'êtes pas autorisé à saisir des présences pour cette classe/matière.", "erreur")
            return redirect(url_for("saisir_presences"))
        eleves_presences = presences.obtenir_presences_classe_matiere_date(id_classe, id_matiere, date_jour)

    return render_template("presences/saisir.html",
                            attributions=attributions_autorisees,
                            id_classe=id_classe, id_matiere=id_matiere, date_jour=date_jour,
                            eleves_presences=eleves_presences, noms_statuts=presences.NOMS_STATUTS)


# ---------- HISTORIQUE DES PRESENCES (Préfet : toutes classes / Enseignant : ses classes) ----------

@app.route("/presences/historique")
@connexion_requise
@role_requis("prefet", "enseignant")
def historique_presences():
    utilisateur = utilisateur_courant()

    if utilisateur.role == "enseignant":
        classes_autorisees = {a["id_classe"] for a in module_notes.lister_attributions_enseignant(utilisateur.id)}
        classes = [c for c in organisation.lister_classes() if c["id"] in classes_autorisees]
    else:
        classes = organisation.lister_classes()

    id_classe = request.args.get("id_classe", type=int)
    date_debut = request.args.get("date_debut") or None
    date_fin = request.args.get("date_fin") or None
    historique = None

    if id_classe:
        if utilisateur.role == "enseignant" and id_classe not in classes_autorisees:
            flash("Vous n'avez pas accès à l'historique de cette classe.", "erreur")
            return redirect(url_for("historique_presences"))
        historique = presences.obtenir_historique_classe(id_classe, date_debut, date_fin)

    return render_template("presences/historique.html", classes=classes, id_classe=id_classe,
                            date_debut=date_debut, date_fin=date_fin, historique=historique,
                            noms_statuts=presences.NOMS_STATUTS)


# ---------- GESTION DES HORAIRES (Préfet uniquement) ----------

@app.route("/horaires", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def gerer_horaires():
    if request.method == "POST":
        id_attribution = int(request.form["id_attribution"])
        jour = request.form["jour"]
        heure_debut = request.form["heure_debut"]
        heure_fin = request.form["heure_fin"]

        if heure_fin <= heure_debut:
            flash("L'heure de fin doit être après l'heure de début.", "erreur")
            return redirect(url_for("gerer_horaires"))

        attribution = next((a for a in module_notes.lister_toutes_attributions() if a["id"] == id_attribution), None)
        if attribution is None:
            flash("Attribution introuvable.", "erreur")
            return redirect(url_for("gerer_horaires"))

        conflit = horaires.verifier_conflit(
            attribution["id_classe"], attribution["id_enseignant"], jour, heure_debut, heure_fin
        )
        if conflit:
            flash(f"Conflit d'horaire : {conflit}", "erreur")
            return redirect(url_for("gerer_horaires"))

        horaires.ajouter_horaire(id_attribution, jour, heure_debut, heure_fin)
        audit.enregistrer(utilisateur_courant(), "Ajout d'un créneau horaire",
                           f"{attribution['classe_niveau']} {attribution['classe_nom']} - {attribution['nom_matiere']} - {jour} {heure_debut}-{heure_fin}")
        flash("Créneau ajouté à l'emploi du temps.", "succes")
        return redirect(url_for("gerer_horaires"))

    return render_template("horaires/gestion.html",
                            horaires_par_jour=horaires.lister_tous_horaires(),
                            jours=horaires.JOURS,
                            attributions=module_notes.lister_toutes_attributions())


@app.route("/horaires/<int:id_horaire>/supprimer", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def supprimer_horaire(id_horaire):
    horaires.supprimer_horaire(id_horaire)
    audit.enregistrer(utilisateur_courant(), "Suppression d'un créneau horaire", f"id {id_horaire}")
    flash("Créneau supprimé.", "succes")
    return redirect(url_for("gerer_horaires"))


# ---------- CONSULTATION DE L'EMPLOI DU TEMPS (tous les rôles, filtré) ----------

@app.route("/emploi-du-temps")
@connexion_requise
def emploi_du_temps():
    utilisateur = utilisateur_courant()

    if utilisateur.role == "prefet":
        return redirect(url_for("gerer_horaires"))

    if utilisateur.role == "enseignant":
        horaires_par_jour = horaires.lister_horaires_enseignant(utilisateur.id)
        titre = "Mon emploi du temps"
    elif utilisateur.role == "eleve":
        eleve = models.obtenir_eleve_par_id(utilisateur.id_eleve) if utilisateur.id_eleve else None
        horaires_par_jour = horaires.lister_horaires_classe(eleve["id_classe"]) if eleve and eleve["id_classe"] else {}
        titre = "Mon emploi du temps"
    elif utilisateur.role == "parent":
        # Un parent peut avoir plusieurs enfants dans des classes différentes :
        # on affiche un emploi du temps par enfant.
        enfants = parents.obtenir_enfants(utilisateur.id)
        emplois_du_temps_enfants = [
            {"enfant": enfant, "horaires_par_jour": horaires.lister_horaires_classe(enfant["id_classe"]) if enfant["id_classe"] else {}}
            for enfant in enfants
        ]
        return render_template("horaires/consulter_parent.html", jours=horaires.JOURS,
                                emplois_du_temps_enfants=emplois_du_temps_enfants)
    else:
        horaires_par_jour = {}
        titre = "Mon emploi du temps"

    return render_template("horaires/consulter.html", jours=horaires.JOURS,
                            horaires_par_jour=horaires_par_jour, titre=titre)


# ---------- FRAIS SCOLAIRES (Préfet uniquement : configuration officielle) ----------

@app.route("/frais", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def liste_frais():
    if request.method == "POST":
        id_classe = int(request.form["id_classe"])
        nom = request.form["nom"].strip()
        montant = float(request.form["montant"])
        devise = request.form["devise"]
        paiements.ajouter_frais(id_classe, nom, montant, devise)
        audit.enregistrer(utilisateur_courant(), "Ajout d'un frais scolaire", f"{nom} - {montant} {devise}")
        flash("Frais ajouté.", "succes")
        return redirect(url_for("liste_frais", id_classe=id_classe))

    id_classe = request.args.get("id_classe", type=int)
    classes = organisation.lister_classes()
    frais_classe = paiements.lister_frais_classe(id_classe) if id_classe else None
    totaux_attendus = paiements.montant_attendu_classe(id_classe) if id_classe else None

    return render_template("paiements/frais.html", classes=classes, id_classe=id_classe,
                            frais_classe=frais_classe, totaux_attendus=totaux_attendus,
                            devises=paiements.DEVISES)


@app.route("/frais/<int:id_frais>/supprimer", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def supprimer_frais(id_frais):
    paiements.supprimer_frais(id_frais)
    audit.enregistrer(utilisateur_courant(), "Suppression d'un frais scolaire", f"id {id_frais}")
    flash("Frais supprimé.", "succes")
    return redirect(request.referrer or url_for("liste_frais"))


# ---------- FINANCE : vue d'ensemble (Préfet + Secrétariat) ----------
# Le secrétariat n'a accès qu'à cette partie "finance" de l'application :
# retrouver un élève et gérer ses paiements, rien d'autre (pas les notes,
# pas les présences, pas l'organisation scolaire).

@app.route("/finance")
@connexion_requise
@role_requis("prefet", "secretariat")
def finance():
    recherche = request.args.get("recherche", "").strip()
    eleves = models.obtenir_tous_les_eleves(recherche if recherche else None)
    lignes = []
    for eleve in eleves:
        soldes = paiements.calculer_soldes(eleve["id"], eleve["id_classe"])
        lignes.append({"eleve": eleve, "soldes": soldes})
    return render_template("paiements/finance.html", lignes=lignes, recherche=recherche)


# ---------- PAIEMENTS D'UN ELEVE (Préfet + Secrétariat) ----------

@app.route("/eleves/<int:id_eleve>/paiements", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet", "secretariat")
def paiements_eleve(id_eleve):
    eleve = models.obtenir_eleve_par_id(id_eleve)
    if eleve is None:
        flash("Élève introuvable.", "erreur")
        return redirect(url_for("finance"))

    if request.method == "POST":
        montant = float(request.form["montant"])
        if montant <= 0:
            flash("Le montant doit être positif.", "erreur")
            return redirect(url_for("paiements_eleve", id_eleve=id_eleve))

        id_paiement = paiements.enregistrer_paiement(
            id_eleve=id_eleve,
            montant=montant,
            devise=request.form["devise"],
            motif=request.form.get("motif", "").strip(),
            mode_paiement=request.form.get("mode_paiement", ""),
            reference=request.form.get("reference", "").strip(),
            id_utilisateur=utilisateur_courant().id,
            date_paiement=request.form.get("date_paiement") or None,
        )
        audit.enregistrer(utilisateur_courant(), "Enregistrement d'un paiement",
                           f"{eleve['prenom']} {eleve['nom']} : {montant} {request.form['devise']}")
        flash("Paiement enregistré.", "succes")
        return redirect(url_for("paiements_eleve", id_eleve=id_eleve))

    soldes = paiements.calculer_soldes(id_eleve, eleve["id_classe"])
    historique = paiements.obtenir_historique_paiements(id_eleve)
    return render_template("paiements/eleve.html", eleve=eleve, soldes=soldes,
                            historique=historique, modes=paiements.MODES_PAIEMENT,
                            devises=paiements.DEVISES)


# ---------- REÇU DE PAIEMENT (PDF) ----------

@app.route("/paiements/<int:id_paiement>/recu")
@connexion_requise
def telecharger_recu(id_paiement):
    utilisateur = utilisateur_courant()
    paiement = paiements.obtenir_paiement(id_paiement)
    if paiement is None:
        flash("Paiement introuvable.", "erreur")
        return redirect(url_for("accueil"))

    id_eleve = paiement["id_eleve"]
    eleve = models.obtenir_eleve_par_id(id_eleve)

    autorise = False
    if utilisateur.role in ("prefet", "secretariat"):
        autorise = True
    elif utilisateur.role == "eleve":
        autorise = utilisateur.id_eleve == id_eleve
    elif utilisateur.role == "parent":
        autorise = parents.parent_est_lie_a_eleve(utilisateur.id, id_eleve)

    if not autorise:
        abort(403)

    # Solde (dans la MÊME devise que ce paiement) au moment du reçu =
    # attendu - (somme des paiements de cette devise faits jusqu'à celui-ci inclus)
    historique = paiements.obtenir_historique_paiements(id_eleve)
    attendu_par_devise = paiements.montant_attendu_classe(eleve["id_classe"]) if eleve["id_classe"] else {"CDF": 0, "USD": 0}
    paiements_jusquici = sum(
        p["montant"] for p in historique if p["id"] <= id_paiement and p["devise"] == paiement["devise"]
    )
    solde_apres = attendu_par_devise[paiement["devise"]] - paiements_jusquici

    chemin_temporaire = os.path.join(tempfile.gettempdir(), f"recu_{id_paiement}.pdf")
    recu.generer_recu_pdf(eleve, paiement, solde_apres, chemin_temporaire)

    audit.enregistrer(utilisateur, "Génération d'un reçu de paiement", f"paiement {id_paiement}")
    return send_file(chemin_temporaire, as_attachment=True, download_name=f"Recu_{id_paiement}.pdf")


# ---------- PARAMETRES DE L'ECOLE (Préfet uniquement) ----------

EXTENSIONS_IMAGE_AUTORISEES = {"png", "jpg", "jpeg"}
DOSSIER_IMAGES_ECOLE = os.path.join("static", "ecole")


def _extension_autorisee(nom_fichier):
    return "." in nom_fichier and nom_fichier.rsplit(".", 1)[1].lower() in EXTENSIONS_IMAGE_AUTORISEES


@app.route("/ecole", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def parametres_ecole():
    if request.method == "POST":
        ecole.mettre_a_jour_parametres(
            nom_ecole=request.form["nom_ecole"],
            adresse=request.form.get("adresse", ""),
            telephone=request.form.get("telephone", ""),
            email=request.form.get("email", ""),
            nom_signataire=request.form.get("nom_signataire", ""),
            titre_signataire=request.form.get("titre_signataire", ""),
        )

        os.makedirs(DOSSIER_IMAGES_ECOLE, exist_ok=True)

        fichier_logo = request.files.get("logo")
        if fichier_logo and fichier_logo.filename and _extension_autorisee(fichier_logo.filename):
            extension = fichier_logo.filename.rsplit(".", 1)[1].lower()
            chemin = os.path.join(DOSSIER_IMAGES_ECOLE, f"logo.{extension}")
            fichier_logo.save(chemin)
            ecole.mettre_a_jour_logo(chemin)

        fichier_cachet = request.files.get("cachet")
        if fichier_cachet and fichier_cachet.filename and _extension_autorisee(fichier_cachet.filename):
            extension = fichier_cachet.filename.rsplit(".", 1)[1].lower()
            chemin = os.path.join(DOSSIER_IMAGES_ECOLE, f"cachet.{extension}")
            fichier_cachet.save(chemin)
            ecole.mettre_a_jour_cachet(chemin)

        audit.enregistrer(utilisateur_courant(), "Mise à jour des paramètres de l'école")
        flash("Paramètres de l'école mis à jour.", "succes")
        return redirect(url_for("parametres_ecole"))

    return render_template("ecole/parametres.html", parametres=ecole.obtenir_parametres())


# ---------- REGLEMENT D'ORDRE INTERIEUR ----------

@app.route("/reglement")
@connexion_requise
def reglement_interieur():
    return render_template("reglement.html", infos=reglement.obtenir_infos(),
                            fichier_existe=reglement.fichier_existe())


@app.route("/reglement/telecharger")
@connexion_requise
def telecharger_reglement():
    if not reglement.fichier_existe():
        flash("Aucun règlement n'a encore été importé.", "erreur")
        return redirect(url_for("reglement_interieur"))
    return send_file(reglement.CHEMIN_FICHIER, as_attachment=True,
                      download_name="Reglement_interieur.pdf")


@app.route("/reglement/importer", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def importer_reglement():
    fichier = request.files.get("fichier")
    if not fichier or not fichier.filename:
        flash("Veuillez choisir un fichier PDF.", "erreur")
        return redirect(url_for("reglement_interieur"))
    if not fichier.filename.lower().endswith(".pdf"):
        flash("Le règlement doit être un fichier PDF.", "erreur")
        return redirect(url_for("reglement_interieur"))

    reglement.remplacer_fichier(fichier)
    audit.enregistrer(utilisateur_courant(), "Import/remplacement du règlement d'ordre intérieur", fichier.filename)
    flash("Règlement d'ordre intérieur mis à jour.", "succes")
    return redirect(url_for("reglement_interieur"))


# ---------- MESSAGES DU PREFET (lecture : Préfet + Enseignant / écriture : Préfet) ----------

@app.route("/messages")
@connexion_requise
@role_requis("prefet", "enseignant")
def liste_messages():
    return render_template("messages/liste.html", messages=module_messages.lister_messages())


@app.route("/messages/creer", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def creer_message():
    if request.method == "POST":
        module_messages.creer_message(request.form["titre"], request.form["contenu"], utilisateur_courant().id)
        audit.enregistrer(utilisateur_courant(), "Publication d'un message", request.form["titre"].strip())
        flash("Message publié.", "succes")
        return redirect(url_for("liste_messages"))
    return render_template("messages/formulaire.html", message=None)


@app.route("/messages/<int:id_message>/modifier", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def modifier_message(id_message):
    message = module_messages.obtenir_message(id_message)
    if message is None:
        flash("Message introuvable.", "erreur")
        return redirect(url_for("liste_messages"))

    if request.method == "POST":
        module_messages.modifier_message(id_message, request.form["titre"], request.form["contenu"])
        audit.enregistrer(utilisateur_courant(), "Modification d'un message", request.form["titre"].strip())
        flash("Message modifié.", "succes")
        return redirect(url_for("liste_messages"))

    return render_template("messages/formulaire.html", message=message)


@app.route("/messages/<int:id_message>/supprimer", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def supprimer_message(id_message):
    module_messages.supprimer_message(id_message)
    audit.enregistrer(utilisateur_courant(), "Suppression d'un message", f"id {id_message}")
    flash("Message supprimé.", "succes")
    return redirect(url_for("liste_messages"))


@app.route("/profil/photo", methods=["POST"])
@connexion_requise
def changer_photo():
    utilisateur = utilisateur_courant()
    fichier = request.files.get("photo")

    # La photo d'un compte "élève" vit sur la fiche élève elle-même
    # (c'est l'identité canonique, qui existe même sans compte de connexion) ;
    # pour tous les autres rôles, elle vit directement sur le compte.
    if utilisateur.role == "eleve" and utilisateur.id_eleve:
        chemin_photo = photos.enregistrer_photo(fichier, os.path.join("static", "photos", "eleves"), str(utilisateur.id_eleve))
        if chemin_photo:
            models.mettre_a_jour_photo_eleve(utilisateur.id_eleve, chemin_photo)
    else:
        chemin_photo = photos.enregistrer_photo(fichier, os.path.join("static", "photos", "utilisateurs"), str(utilisateur.id))
        if chemin_photo:
            utilisateurs.mettre_a_jour_photo(utilisateur.id, chemin_photo)

    if fichier and fichier.filename and not chemin_photo:
        flash("La photo n'a pas pu être enregistrée (fichier image invalide).", "erreur")
    elif chemin_photo:
        audit.enregistrer(utilisateur, "Changement de photo de profil")
        flash("Photo mise à jour.", "succes")
    else:
        flash("Veuillez choisir une image.", "erreur")

    return redirect(url_for("profil"))


# ---------- GESTION DES UTILISATEURS (Préfet uniquement) ----------

@app.route("/utilisateurs")
@connexion_requise
@role_requis("prefet")
def liste_utilisateurs():
    filtre_role = request.args.get("role", "")
    comptes = utilisateurs.lister_utilisateurs()
    if filtre_role:
        comptes = [c for c in comptes if c["role"] == filtre_role]
    return render_template("utilisateurs/liste.html", comptes=comptes, noms_roles=NOMS_ROLES, filtre_role=filtre_role)


@app.route("/utilisateurs/ajouter", methods=["GET", "POST"])
@connexion_requise
@role_requis("prefet")
def ajouter_utilisateur():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        mot_de_passe = request.form["mot_de_passe"]

        if len(mot_de_passe) < 6:
            flash("Le mot de passe doit contenir au moins 6 caractères.", "erreur")
            return render_template("utilisateurs/ajouter.html", noms_roles=NOMS_ROLES,
                                    eleves=models.obtenir_tous_les_eleves())

        if utilisateurs.email_existe(email):
            flash("Un compte avec cet email existe déjà.", "erreur")
            return render_template("utilisateurs/ajouter.html", noms_roles=NOMS_ROLES,
                                    eleves=models.obtenir_tous_les_eleves())

        role = request.form["role"]
        id_eleve = request.form.get("id_eleve") or None
        ids_enfants = request.form.getlist("ids_enfants")

        id_nouvel_utilisateur = utilisateurs.ajouter_utilisateur(
            nom_complet=request.form["nom_complet"].strip(),
            email=email,
            mot_de_passe=mot_de_passe,
            role=role,
            id_eleve=id_eleve if role == "eleve" else None,
            matricule_enseignant=request.form.get("matricule_enseignant", "").strip() if role == "enseignant" else None,
            specialite=request.form.get("specialite", "").strip() if role == "enseignant" else None,
        )

        if role == "parent" and ids_enfants:
            for id_enfant in ids_enfants:
                parents.lier_enfant(id_nouvel_utilisateur, int(id_enfant))

        fichier_photo = request.files.get("photo")
        if fichier_photo and fichier_photo.filename:
            if role == "eleve" and id_eleve:
                chemin_photo = photos.enregistrer_photo(fichier_photo, os.path.join("static", "photos", "eleves"), str(id_eleve))
                if chemin_photo:
                    models.mettre_a_jour_photo_eleve(int(id_eleve), chemin_photo)
            else:
                chemin_photo = photos.enregistrer_photo(fichier_photo, os.path.join("static", "photos", "utilisateurs"), str(id_nouvel_utilisateur))
                if chemin_photo:
                    utilisateurs.mettre_a_jour_photo(id_nouvel_utilisateur, chemin_photo)

        audit.enregistrer(utilisateur_courant(), "Création d'un compte utilisateur",
                           f"{request.form['nom_complet'].strip()} ({email}) - rôle : {role}")
        flash("Le compte a été créé avec succès.", "succes")
        return redirect(url_for("liste_utilisateurs"))

    tous_les_eleves = models.obtenir_tous_les_eleves()
    return render_template("utilisateurs/ajouter.html", noms_roles=NOMS_ROLES, eleves=tous_les_eleves)


@app.route("/utilisateurs/<int:id_utilisateur>/statut", methods=["POST"])
@connexion_requise
@role_requis("prefet")
def basculer_statut_utilisateur(id_utilisateur):
    utilisateur = utilisateur_courant()
    if id_utilisateur == utilisateur.id:
        flash("Vous ne pouvez pas désactiver votre propre compte.", "erreur")
        return redirect(url_for("liste_utilisateurs"))

    compte = utilisateurs.obtenir_utilisateur_par_id(id_utilisateur)
    nouveau_statut = utilisateurs.basculer_statut_compte(id_utilisateur)
    libelle = "activé" if nouveau_statut else "désactivé"
    audit.enregistrer(utilisateur, f"Compte {libelle}", f"{compte.nom_complet} ({compte.email})")
    flash(f"Le compte de {compte.nom_complet} a été {libelle}.", "succes")
    return redirect(url_for("liste_utilisateurs"))


# ---------- HISTORIQUE DES ACTIONS (Préfet uniquement) ----------

@app.route("/historique")
@connexion_requise
@role_requis("prefet")
def historique():
    actions = audit.obtenir_journal()
    return render_template("historique.html", actions=actions)


if __name__ == "__main__":
    # SÉCURITÉ : debug=True affiche un débogueur interactif en cas d'erreur,
    # qui peut permettre d'exécuter du code arbitraire sur le serveur.
    # Ne JAMAIS l'activer sur un serveur accessible publiquement.
    mode_debug = os.environ.get("EDUVIA_DEBUG", "0") == "1"
    app.run(debug=mode_debug, host=os.environ.get("EDUVIA_HOST", "127.0.0.1"),
            port=int(os.environ.get("EDUVIA_PORT", "5000")))
