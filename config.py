"""
Configuration de l'application - Gestion des créances fiscales
Connexion à MySQL via XAMPP (module MySQL uniquement).
"""

import os

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY")

    # Paramètres MySQL (XAMPP) - phpMyAdmin par défaut : user=root, pas de mot de passe
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "gestion_creances_fiscales")
    MYSQL_SSL_CA = os.environ.get("MYSQL_SSL_CA")
    # Dossier où sont stockés les PDF de mise en demeure générés
    DOSSIER_PDF = os.path.join(os.path.dirname(__file__), "static", "relances_pdf")

    # Nombre de jours après échéance avant relance automatique
    DELAI_TOLERANCE_JOURS = 0
