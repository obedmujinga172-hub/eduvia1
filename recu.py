"""
recu.py
--------
Génère un reçu de paiement en PDF pour un paiement enregistré, habillé
avec les paramètres de l'école (logo, coordonnées, signature, cachet —
voir ecole.py), sur le même principe que bulletin.py.
"""

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER

import ecole


def generer_recu_pdf(eleve, paiement, solde_apres, chemin_fichier):
    """Crée un fichier PDF de reçu à l'emplacement 'chemin_fichier'."""
    parametres = ecole.obtenir_parametres()
    styles = getSampleStyleSheet()
    style_titre = ParagraphStyle("Titre", parent=styles["Title"], alignment=TA_CENTER, fontSize=16)
    style_sous_titre = ParagraphStyle("SousTitre", parent=styles["Normal"], alignment=TA_CENTER, fontSize=10)
    style_document = ParagraphStyle("Document", parent=styles["Normal"], alignment=TA_CENTER, fontSize=12)

    document = SimpleDocTemplate(chemin_fichier, pagesize=A4,
                                  topMargin=1.5 * cm, bottomMargin=2 * cm)
    elements = []

    # ---------- En-tête : logo + nom et coordonnées de l'école ----------
    if parametres["chemin_logo"] and os.path.exists(parametres["chemin_logo"]):
        elements.append(Image(parametres["chemin_logo"], width=2.5 * cm, height=2.5 * cm, hAlign="CENTER"))
        elements.append(Spacer(1, 0.2 * cm))

    elements.append(Paragraph(parametres["nom_ecole"] or "EDUVIA", style_titre))

    coordonnees = " · ".join(filter(None, [parametres["adresse"], parametres["telephone"], parametres["email"]]))
    if coordonnees:
        elements.append(Paragraph(coordonnees, style_sous_titre))

    elements.append(Spacer(1, 0.4 * cm))
    elements.append(Paragraph("Reçu de paiement", style_document))
    elements.append(Spacer(1, 0.7 * cm))

    # ---------- Informations du reçu ----------
    classe_texte = f"{eleve['classe_niveau']} - {eleve['classe_nom']}" if eleve["classe_nom"] else "Non assignée"

    infos = [
        ["Reçu N° :", str(paiement["id"])],
        ["Date :", paiement["date_paiement"]],
        ["Élève :", f"{eleve['nom']} {eleve['postnom']} {eleve['prenom']}"],
        ["Matricule :", eleve["matricule"]],
        ["Classe :", classe_texte],
        ["Motif du paiement :", paiement["motif"] or "—"],
        ["Mode de paiement :", paiement["mode_paiement"] or "—"],
        ["Référence :", paiement["reference"] or "—"],
    ]
    tableau_infos = Table(infos, colWidths=[4.5 * cm, 10.5 * cm])
    tableau_infos.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(tableau_infos)
    elements.append(Spacer(1, 0.8 * cm))

    tableau_montant = Table([
        ["Montant payé", f"{paiement['montant']:,.2f} {paiement['devise']}"],
        ["Solde restant après ce paiement", f"{solde_apres:,.2f} {paiement['devise']}"],
    ], colWidths=[10.5 * cm, 4.5 * cm])
    tableau_montant.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 11),
    ]))
    elements.append(tableau_montant)
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
