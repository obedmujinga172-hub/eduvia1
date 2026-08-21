"""
bulletin.py
------------
Génère un bulletin scolaire en PDF pour un élève, pour une période donnée,
à partir de ses notes (voir notes.py), habillé avec les paramètres de
l'école (logo, coordonnées, signature, cachet — voir ecole.py).
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

import notes as module_notes
import ecole


def generer_bulletin_pdf(eleve, periode, chemin_fichier):
    """
    Crée un fichier PDF de bulletin à l'emplacement 'chemin_fichier'.
    'eleve' est une ligne provenant de models.obtenir_eleve_par_id (avec classe/option/année).
    """
    parametres = ecole.obtenir_parametres()
    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle("Titre", parent=styles["Title"], alignment=TA_CENTER, fontSize=16)
    style_sous_titre = ParagraphStyle("SousTitre", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10)
    style_document = ParagraphStyle("Document", parent=styles["Normal"], alignment=TA_CENTER, fontSize=12)

    document = SimpleDocTemplate(chemin_fichier, pagesize=A4,
                                  topMargin=1.5 * cm, bottomMargin=2 * cm)
    elements = []

    # ---------- En-tête : logo (si configuré) + nom et coordonnées de l'école ----------
    if parametres["chemin_logo"] and os.path.exists(parametres["chemin_logo"]):
        elements.append(Image(parametres["chemin_logo"], width=2.5 * cm, height=2.5 * cm, hAlign="CENTER"))
        elements.append(Spacer(1, 0.2 * cm))

    elements.append(Paragraph(parametres["nom_ecole"] or "EDUVIA", style_titre))

    coordonnees = " · ".join(filter(None, [parametres["adresse"], parametres["telephone"], parametres["email"]]))
    if coordonnees:
        elements.append(Paragraph(coordonnees, style_sous_titre))

    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph("Bulletin scolaire", style_document))
    elements.append(Spacer(1, 0.5 * cm))

    # ---------- Informations de l'élève ----------
    classe_texte = f"{eleve['classe_niveau']} - {eleve['classe_nom']}" if eleve["classe_nom"] else "Non assignée"
    if eleve["option_nom"]:
        classe_texte += f" ({eleve['option_nom']})"

    infos = [
        ["Élève :", f"{eleve['nom']} {eleve['postnom']} {eleve['prenom']}"],
        ["Matricule :", eleve["matricule"]],
        ["Classe :", classe_texte],
        ["Année scolaire :", eleve["annee_scolaire"] or "—"],
        ["Période :", periode],
    ]
    tableau_infos = Table(infos, colWidths=[4 * cm, 11 * cm])
    tableau_infos.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))

    if eleve["chemin_photo"] and os.path.exists(eleve["chemin_photo"]):
        photo_eleve = Image(eleve["chemin_photo"], width=2.5 * cm, height=2.5 * cm)
        tableau_avec_photo = Table([[tableau_infos, photo_eleve]], colWidths=[11 * cm, 2.5 * cm])
        tableau_avec_photo.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
        elements.append(tableau_avec_photo)
    else:
        elements.append(tableau_infos)
    elements.append(Spacer(1, 0.7 * cm))

    # ---------- Tableau des notes ----------
    notes_eleve = module_notes.obtenir_notes_eleve(eleve["id"], periode)
    moyenne = module_notes.calculer_moyenne(eleve["id"], periode)

    donnees_tableau = [["Matière", "Note / 20"]]
    for note in notes_eleve:
        donnees_tableau.append([note["nom_matiere"], f"{note['valeur']:.2f}"])
    if not notes_eleve:
        donnees_tableau.append(["Aucune note enregistrée pour cette période", ""])

    tableau_notes = Table(donnees_tableau, colWidths=[11 * cm, 4 * cm])
    tableau_notes.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "CENTER"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fb")]),
    ]))
    elements.append(tableau_notes)
    elements.append(Spacer(1, 0.7 * cm))

    texte_moyenne = f"Moyenne générale : {moyenne:.2f} / 20" if moyenne is not None else "Moyenne générale : —"
    elements.append(Paragraph(f"<b>{texte_moyenne}</b>", ParagraphStyle("Moyenne", parent=styles["Normal"], fontSize=12)))
    elements.append(Spacer(1, 1.5 * cm))

    # ---------- Signature et cachet ----------
    cellule_signature = []
    if parametres["nom_signataire"] or parametres["titre_signataire"]:
        cellule_signature.append(Paragraph(parametres["titre_signataire"] or "", style_sous_titre))
        cellule_signature.append(Spacer(1, 1.2 * cm))
        cellule_signature.append(Paragraph(parametres["nom_signataire"] or "", ParagraphStyle(
            "Signataire", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10, fontName="Helvetica-Bold")))
    else:
        cellule_signature.append(Spacer(1, 1.5 * cm))

    cellule_cachet = []
    if parametres["chemin_cachet"] and os.path.exists(parametres["chemin_cachet"]):
        cellule_cachet.append(Image(parametres["chemin_cachet"], width=3 * cm, height=3 * cm, hAlign="CENTER"))
    else:
        cellule_cachet.append(Paragraph("(cachet de l'école)", ParagraphStyle(
            "Cachet", parent=styles["Normal"], alignment=TA_CENTER, fontSize=8, textColor=colors.grey)))

    tableau_bas = Table([[cellule_signature, cellule_cachet]], colWidths=[8 * cm, 7 * cm])
    tableau_bas.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    elements.append(tableau_bas)

    document.build(elements)
