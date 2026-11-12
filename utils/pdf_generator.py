"""
Génération automatique du PDF de "mise en demeure" pour une dette en retard.
Utilise ReportLab + qrcode (le QR code encode la référence du dossier afin
qu'un agent puisse scanner le document et retrouver le dossier dans l'appli).
"""

import os
import io
from datetime import datetime, date

import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors

from config import Config

NAVY = colors.HexColor("#0f2942")
CYAN = colors.HexColor("#00b8d9")


def _generer_qrcode(contenu):
    """Génère un QR code en mémoire (PNG) et retourne un objet utilisable par ReportLab."""
    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(contenu)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f2942", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def generer_mise_en_demeure(dette):
    """
    Génère un PDF de mise en demeure pour une dette (dict provenant de db.get_dette
    ou db.dettes_en_retard_non_relancees) et renvoie le chemin du fichier créé.
    """
    os.makedirs(Config.DOSSIER_PDF, exist_ok=True)

    reference = f"D-{dette['id']:05d}"
    nom_fichier = f"mise_en_demeure_{reference}_{datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
    chemin_complet = os.path.join(Config.DOSSIER_PDF, nom_fichier)

    nom_complet = f"{dette.get('nom_contribuable','')} {dette.get('prenom_contribuable','') or ''}".strip()

    # Contenu encodé dans le QR code (permet de retrouver le dossier en le scannant)
    contenu_qr = (
        f"Dossier: {reference}\n"
        f"Contribuable: {nom_complet}\n"
        f"NIF: {dette.get('nif','')}\n"
        f"Montant: {dette['montant']} Ar\n"
        f"Echeance: {dette['date_echeance']}"
    )
    qr_image = _generer_qrcode(contenu_qr)

    doc = SimpleDocTemplate(
        chemin_complet, pagesize=A4,
        topMargin=20 * mm, bottomMargin=20 * mm, leftMargin=20 * mm, rightMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Entete", fontSize=15, leading=19, alignment=TA_CENTER,
                               spaceAfter=6, textColor=NAVY, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="SousEntete", fontSize=9.5, alignment=TA_CENTER,
                               textColor=colors.HexColor("#4a6178")))
    styles.add(ParagraphStyle(name="Droite", alignment=TA_RIGHT, fontSize=10))
    styles.add(ParagraphStyle(name="Corps", fontSize=10.5, leading=15, spaceAfter=10))
    styles.add(ParagraphStyle(name="RefBox", fontSize=10, leading=14, textColor=colors.white))

    story = []

    story.append(Paragraph("RÉPUBLIQUE DE MADAGASCAR", styles["SousEntete"]))
    story.append(Paragraph("ADMINISTRATION FISCALE", styles["SousEntete"]))
    story.append(Paragraph("Direction Générale des Impôts", styles["SousEntete"]))
    story.append(Spacer(1, 10))
    story.append(Paragraph("MISE EN DEMEURE", styles["Entete"]))
    story.append(Paragraph("Notification de relance pour créance fiscale impayée", styles["SousEntete"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph(f"Numéro fiscal : {dette.get('nif','')}", styles["Corps"]))
    story.append(Paragraph(f"Nom : {dette.get('nom_contribuable','')}", styles["Corps"]))
    if dette.get("prenom_contribuable"):
        story.append(Paragraph(f"Prénom : {dette.get('prenom_contribuable')}", styles["Corps"]))
    if dette.get("adresse"):
        story.append(Paragraph(f"Adresse : {dette['adresse']}", styles["Corps"]))

    story.append(Spacer(1, 4))

    data = [
        ["Référence dossier", reference],
        ["Montant dû", f"{dette['montant']:,.0f} Ar".replace(",", " ")],
        ["Type d'impôt", dette["nature_impot"]],
        ["Date d'échéance", dette["date_echeance"].strftime("%d/%m/%Y") if hasattr(dette["date_echeance"], "strftime") else str(dette["date_echeance"])],
    ]
    table = Table(data, colWidths=[55 * mm, 100 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), NAVY),
        ("TEXTCOLOR", (0, 0), (0, -1), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(table)
    story.append(Spacer(1, 16))

    texte = (
        "Nous vous informons que votre dette fiscale mentionnée ci-dessus est arrivée à échéance. "
        "Conformément aux dispositions du Code Général des Impôts, nous vous mettons en demeure de "
        "régulariser votre situation dans un délai de <b>15 jours</b> à compter de la réception de la "
        "présente notification.<br/><br/>"
        "À défaut de règlement dans ce délai, des pénalités de retard ainsi que des poursuites en "
        "recouvrement pourront être engagées, conformément à la réglementation fiscale en vigueur.<br/><br/>"
        "Vous pouvez scanner le QR code ci-dessous pour retrouver la référence exacte de votre dossier."
    )
    story.append(Paragraph(texte, styles["Corps"]))
    story.append(Spacer(1, 18))

    # --- QR code + zone signature, côte à côte ---
    img_qr = Image(qr_image, width=28 * mm, height=28 * mm)
    bloc = Table(
        [[img_qr, Paragraph(
            f"Fait à Antananarivo, le {date.today().strftime('%d/%m/%Y')}"
            f"<br/><br/><br/>L'Administration Fiscale", styles["Droite"])]],
        colWidths=[40 * mm, 115 * mm],
    )
    bloc.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(bloc)

    doc.build(story)
    return chemin_complet
