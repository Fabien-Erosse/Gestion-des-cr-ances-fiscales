"""
Script automatisé de vérification quotidienne des échéances fiscales.

Ce script peut être exécuté :
  1) manuellement :         python scripts/verifier_echeances.py
  2) via le planificateur APScheduler intégré à app.py (au démarrage du serveur)
  3) via une tâche planifiée Windows / cron Linux, ex (cron) :
        0 6 * * *  cd /chemin/vers/projet6 && python scripts/verifier_echeances.py

Pour chaque dette dont la date d'échéance est dépassée et non soldée :
  - passe son statut de "en_attente" à "echue"
  - génère un PDF de mise en demeure
  - simule/enregistre l'envoi d'une notification (email + SMS)
  - met à jour le statut de la dette en base ("mise_en_demeure")
  - enregistre l'action dans l'historique des relances
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db
from utils.pdf_generator import generer_mise_en_demeure
from utils.notifications import envoyer_email, envoyer_sms


def verifier_et_relancer():
    # 1) Fait passer automatiquement "en_attente" -> "echue" si échéance dépassée
    db.marquer_echues()

    dettes = db.dettes_en_retard_non_relancees()
    print(f"[{len(dettes)}] dette(s) en retard détectée(s).")

    for dette in dettes:
        # 2) Génération du PDF de mise en demeure
        chemin_pdf = generer_mise_en_demeure(dette)
        print(f" -> PDF généré : {chemin_pdf}")

        # 3) Simulation/envoi des notifications
        sujet = f"Mise en demeure - Dossier D-{dette['id']:05d}"
        corps = (
            f"Bonjour {dette['nom_contribuable']},\n\n"
            f"Votre créance fiscale ({dette['nature_impot']}, {dette['montant']} Ar) "
            f"est en retard depuis le {dette['date_echeance']}. "
            f"Merci de régulariser votre situation dans les 15 jours.\n\n"
            f"Direction Générale des Impôts."
        )
        statut_email = envoyer_email(dette.get("email"), sujet, corps)
        envoyer_sms(dette.get("telephone"), f"Relance fiscale D-{dette['id']:05d} - {dette['montant']} Ar en retard.")

        # 4) Enregistrement de la relance en base
        db.enregistrer_relance(
            id_dette=dette["id"],
            type_relance="mise_en_demeure",
            canal="email",
            statut_envoi=statut_email,
            fichier_pdf=chemin_pdf,
        )

        # 5) Mise à jour du statut du dossier
        db.modifier_statut_dette(dette["id"], "mise_en_demeure")
        print(f" -> Dossier D-{dette['id']:05d} passé au statut 'mise_en_demeure'.")


if __name__ == "__main__":
    verifier_et_relancer()
