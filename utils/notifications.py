
"""
Simulation des notifications pour la démonstration.
Aucun email réel ni SMS réel ne sera envoyé.
"""

import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

logger = logging.getLogger("notifications")

# Sécurité : les envois réels sont désactivés par défaut.
ENVOI_EMAIL_ACTIF = False


def construire_message(dette, formel=False):
    """Construit le texte de la notification."""
    nom_complet = (
        f"{dette.get('prenom_contribuable', '')} "
        f"{dette['nom_contribuable']}"
    ).strip()

    date_ech = dette["date_echeance"]
    date_ech_str = (
        date_ech.strftime("%d/%m/%Y")
        if hasattr(date_ech, "strftime")
        else str(date_ech)
    )

    montant_str = f"{dette['montant']:,.0f} Ar".replace(",", " ")

    if formel:
        return (
            f"Bonjour M./Mme {nom_complet},\n\n"
            f"Votre dette fiscale ({dette['nature_impot']}) "
            f"d'un montant de {montant_str} est arrivée à échéance "
            f"le {date_ech_str}.\n\n"
            f"Simulation de mise en demeure : délai de 15 jours.\n\n"
            f"Cordialement,\nAdministration Fiscale"
        )

    return (
        f"Bonjour M./Mme {nom_complet},\n\n"
        f"Votre dette fiscale ({dette['nature_impot']}) "
        f"d'un montant de {montant_str} est arrivée à échéance "
        f"le {date_ech_str}.\n\n"
        f"Veuillez procéder au règlement dans les meilleurs délais.\n\n"
        f"Cordialement,\nAdministration Fiscale"
    )


def envoyer_email(destinataire, sujet, corps):
    """Simule l'envoi d'un email sans contacter Gmail."""

    if not ENVOI_EMAIL_ACTIF:
        logger.info(
            "[SIMULATION EMAIL] Destinataire : %s | Sujet : %s",
            destinataire,
            sujet
        )
        return "simule"

    # Aucun envoi réel n'est autorisé dans cette version de démonstration.
    logger.warning("Envoi réel désactivé pour cette application.")
    return "simule"


def envoyer_sms(numero, message):
    """Simule l'envoi d'un SMS."""

    logger.info(
        "[SIMULATION SMS] Numéro : %s | Message : %s",
        numero,
        message
    )

    return "simule"
