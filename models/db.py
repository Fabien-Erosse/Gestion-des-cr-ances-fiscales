"""
Module de connexion à la base MySQL (XAMPP) et fonctions d'accès aux données.
Architecture MVC : ce module joue le rôle du "Modèle".

Workflow des statuts d'une dette :
  en_attente -> echue -> relance -> mise_en_demeure -> payee
"""

import mysql.connector
from config import Config


def get_connection():
    """Ouvre une connexion à la base MySQL gérée par XAMPP."""
    return mysql.connector.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        charset="utf8mb4",
        collation="utf8mb4_unicode_ci",
    )


# ------------------------ Utilisateurs ------------------------

def get_utilisateur_par_nom(nom_utilisateur):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM utilisateurs WHERE nom_utilisateur = %s", (nom_utilisateur,))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user


# ------------------------ Contribuables ------------------------

def liste_contribuables(recherche=None):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    if recherche:
        motif = f"%{recherche}%"
        cur.execute(
            """SELECT * FROM contribuables
               WHERE nom LIKE %s OR prenom LIKE %s OR nif LIKE %s
               ORDER BY nom""",
            (motif, motif, motif),
        )
    else:
        cur.execute("SELECT * FROM contribuables ORDER BY nom")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_contribuable(id_contribuable):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM contribuables WHERE id = %s", (id_contribuable,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def ajouter_contribuable(nom, prenom, nif, adresse, email, telephone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO contribuables (nom, prenom, nif, adresse, email, telephone) VALUES (%s,%s,%s,%s,%s,%s)",
        (nom, prenom, nif, adresse, email, telephone),
    )
    conn.commit()
    cur.close()
    conn.close()


def modifier_contribuable(id_contribuable, nom, prenom, nif, adresse, email, telephone):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE contribuables SET nom=%s, prenom=%s, nif=%s, adresse=%s, email=%s, telephone=%s WHERE id=%s",
        (nom, prenom, nif, adresse, email, telephone, id_contribuable),
    )
    conn.commit()
    cur.close()
    conn.close()


def supprimer_contribuable(id_contribuable):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM contribuables WHERE id = %s", (id_contribuable,))
    conn.commit()
    cur.close()
    conn.close()


# ------------------------ Dettes ------------------------

def liste_dettes():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT d.*, c.nom AS nom_contribuable, c.prenom AS prenom_contribuable,
               c.nif, c.email, c.telephone, c.adresse
        FROM dettes d
        JOIN contribuables c ON c.id = d.id_contribuable
        ORDER BY d.date_echeance
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def get_dette(id_dette):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT d.*, c.nom AS nom_contribuable, c.prenom AS prenom_contribuable,
               c.nif, c.email, c.telephone, c.adresse
        FROM dettes d
        JOIN contribuables c ON c.id = d.id_contribuable
        WHERE d.id = %s
    """, (id_dette,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def ajouter_dette(id_contribuable, nature_impot, montant, date_emission, date_echeance, statut="en_attente"):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO dettes (id_contribuable, nature_impot, montant, date_emission, date_echeance, statut)
           VALUES (%s,%s,%s,%s,%s,%s)""",
        (id_contribuable, nature_impot, montant, date_emission, date_echeance, statut),
    )
    conn.commit()
    cur.close()
    conn.close()


def modifier_statut_dette(id_dette, statut):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE dettes SET statut = %s WHERE id = %s", (statut, id_dette))
    conn.commit()
    cur.close()
    conn.close()


def marquer_echues():
    """Fait passer automatiquement 'en_attente' -> 'echue' pour les dettes dont l'échéance est dépassée."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        UPDATE dettes SET statut = 'echue'
        WHERE statut = 'en_attente' AND date_echeance < CURDATE()
    """)
    conn.commit()
    cur.close()
    conn.close()


def dettes_en_retard_non_relancees():
    """Dettes échues (échéance dépassée) qui n'ont pas encore été mises en demeure ni soldées."""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT d.*, c.nom AS nom_contribuable, c.prenom AS prenom_contribuable,
               c.nif, c.email, c.telephone, c.adresse
        FROM dettes d
        JOIN contribuables c ON c.id = d.id_contribuable
        WHERE d.date_echeance < CURDATE() AND d.statut IN ('en_attente', 'echue')
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


# ------------------------ Relances ------------------------

def liste_relances():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT r.*, d.nature_impot, d.montant, c.nom AS nom_contribuable, c.prenom AS prenom_contribuable
        FROM relances r
        JOIN dettes d ON d.id = r.id_dette
        JOIN contribuables c ON c.id = d.id_contribuable
        ORDER BY r.date_relance DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def derniere_relance_pour_dette(id_dette):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT * FROM relances WHERE id_dette = %s ORDER BY date_relance DESC LIMIT 1", (id_dette,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def enregistrer_relance(id_dette, type_relance, canal, statut_envoi, fichier_pdf):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """INSERT INTO relances (id_dette, type_relance, canal, statut_envoi, fichier_pdf)
           VALUES (%s,%s,%s,%s,%s)""",
        (id_dette, type_relance, canal, statut_envoi, fichier_pdf),
    )
    conn.commit()
    cur.close()
    conn.close()


# ------------------------ Statistiques / graphiques ------------------------

def statistiques():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)

    cur.execute("SELECT COUNT(*) AS total, SUM(montant) AS montant_total FROM dettes")
    total = cur.fetchone()

    cur.execute("SELECT COUNT(*) AS n FROM contribuables")
    nb_contribuables = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM dettes WHERE statut IN ('echue','relance','mise_en_demeure')")
    nb_impayees = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM relances")
    nb_relances = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n FROM dettes WHERE statut = 'mise_en_demeure'")
    nb_mise_en_demeure = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) AS n, SUM(montant) AS m FROM dettes WHERE statut='payee'")
    payees = cur.fetchone()

    # Répartition par nature d'impôt (pour l'histogramme)
    cur.execute("""
        SELECT nature_impot, COUNT(*) AS nombre
        FROM dettes GROUP BY nature_impot ORDER BY nombre DESC, nature_impot
    """)
    par_nature = cur.fetchall()

    # Répartition par statut (pour le camembert)
    cur.execute("SELECT statut, COUNT(*) AS nombre FROM dettes GROUP BY statut")
    par_statut = {r["statut"]: r["nombre"] for r in cur.fetchall()}

    cur.close()
    conn.close()

    total_montant = float(total["montant_total"] or 0)
    montant_paye = float(payees["m"] or 0)
    taux = round((montant_paye / total_montant) * 100, 1) if total_montant else 0

    return {
        "total_dettes": total["total"] or 0,
        "montant_total": total_montant,
        "nb_contribuables": nb_contribuables,
        "nb_impayees": nb_impayees,
        "nb_relances": nb_relances,
        "nb_mise_en_demeure": nb_mise_en_demeure,
        "taux_recouvrement": taux,
        "par_nature": par_nature,
        "par_statut": {
            "en_attente": par_statut.get("en_attente", 0),
            "echue": par_statut.get("echue", 0),
            "relance": par_statut.get("relance", 0),
            "mise_en_demeure": par_statut.get("mise_en_demeure", 0),
            "payee": par_statut.get("payee", 0),
        },
    }
