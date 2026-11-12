"""
Application Flask - Gestion des créances fiscales
Plateforme automatisée de suivi des notifications de redressement
et de relance des créances fiscales.

Architecture MVC :
  - Modèle      -> models/db.py
  - Vue         -> templates/*.html + static/css/style.css
  - Contrôleur  -> le présent fichier app.py (routes)
"""

import os
import json
from functools import wraps
from datetime import date, datetime

import bcrypt
from mysql.connector.errors import IntegrityError
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash, send_file
)
from flask_wtf.csrf import CSRFProtect
from apscheduler.schedulers.background import BackgroundScheduler

from config import Config
from models import db
from utils.pdf_generator import generer_mise_en_demeure
from utils.notifications import envoyer_email, envoyer_sms
from scripts.verifier_echeances import verifier_et_relancer

app = Flask(__name__)
app.config.from_object(Config)

csrf = CSRFProtect(app)



# --------------------------- Libellés en français (accents corrects) ---------------------------

LIBELLES_STATUT = {
    "en_attente": "En attente",
    "echue": "Échue",
    "relance": "Relance",
    "mise_en_demeure": "Mise en demeure",
    "payee": "Payée",
}
JOURS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
MOIS_FR = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet",
           "août", "septembre", "octobre", "novembre", "décembre"]


@app.template_filter("libelle_statut")
def libelle_statut(code):
    return LIBELLES_STATUT.get(code, str(code).replace("_", " ").capitalize())


@app.context_processor
def injecter_date_fr():
    d = date.today()
    return {"date_fr": f"{JOURS_FR[d.weekday()].capitalize()} {d.day} {MOIS_FR[d.month - 1]} {d.year}"}

# --------------------------- Sécurité / session ---------------------------

def login_required(vue):
    @wraps(vue)
    def enveloppe(*args, **kwargs):
        if "utilisateur" not in session:
            return redirect(url_for("login"))
        return vue(*args, **kwargs)
    return enveloppe


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifiant = request.form.get("identifiant", "").strip()
        mot_de_passe = request.form.get("mot_de_passe", "").encode("utf-8")

        utilisateur = db.get_utilisateur_par_nom(identifiant)
        if utilisateur and bcrypt.checkpw(mot_de_passe, utilisateur["mot_de_passe_hash"].encode("utf-8")):
            session["utilisateur"] = utilisateur["nom_utilisateur"]
            session["role"] = utilisateur["role"]
            return redirect(url_for("dashboard"))

        flash("Identifiant ou mot de passe incorrect.", "erreur")
        return redirect(url_for("login"))

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --------------------------- Tableau de bord ---------------------------

@app.route("/")
@login_required
def dashboard():
    db.marquer_echues()
    dettes = db.liste_dettes()
    stats = db.statistiques()

    labels_nature = [d["nature_impot"] for d in stats["par_nature"]]
    valeurs_nature = [d["nombre"] for d in stats["par_nature"]]

    return render_template(
        "dashboard.html", dettes=dettes, stats=stats, today=date.today(),
        labels_nature=json.dumps(labels_nature), valeurs_nature=json.dumps(valeurs_nature),
        statut_labels=json.dumps(["Payées", "En attente", "Échues", "Relance", "Mise en demeure"]),
        statut_valeurs=json.dumps([
            stats["par_statut"]["payee"], stats["par_statut"]["en_attente"],
            stats["par_statut"]["echue"], stats["par_statut"]["relance"],
            stats["par_statut"]["mise_en_demeure"],
        ]),
    )


# --------------------------- Contribuables ---------------------------

@app.route("/contribuables")
@login_required
def contribuables():
    recherche = request.args.get("q", "").strip()
    return render_template("contribuables.html", contribuables=db.liste_contribuables(recherche), recherche=recherche)


@app.route("/contribuables/ajouter", methods=["GET", "POST"])
@login_required
def ajouter_contribuable():
    if request.method == "POST":
        try:
            db.ajouter_contribuable(
                request.form["nom"], request.form.get("prenom"), request.form["nif"],
                request.form.get("adresse"), request.form.get("email"), request.form.get("telephone"),
            )
            flash("Contribuable ajouté avec succès.", "succes")
            return redirect(url_for("contribuables"))
        except IntegrityError:
            flash(f"Ce numéro fiscal (NIF) « {request.form['nif']} » est déjà utilisé par un autre contribuable.", "erreur")
            return render_template("contribuable_form.html", contribuable=request.form)
    return render_template("contribuable_form.html", contribuable=None)


@app.route("/contribuables/modifier/<int:id_contribuable>", methods=["GET", "POST"])
@login_required
def modifier_contribuable(id_contribuable):
    if request.method == "POST":
        try:
            db.modifier_contribuable(
                id_contribuable, request.form["nom"], request.form.get("prenom"), request.form["nif"],
                request.form.get("adresse"), request.form.get("email"), request.form.get("telephone"),
            )
            flash("Contribuable modifié avec succès.", "succes")
            return redirect(url_for("contribuables"))
        except IntegrityError:
            flash(f"Ce numéro fiscal (NIF) « {request.form['nif']} » est déjà utilisé par un autre contribuable.", "erreur")
            return render_template("contribuable_form.html", contribuable=request.form)
    return render_template("contribuable_form.html", contribuable=db.get_contribuable(id_contribuable))


@app.route("/contribuables/supprimer/<int:id_contribuable>", methods=["POST"])
@login_required
def supprimer_contribuable(id_contribuable):
    db.supprimer_contribuable(id_contribuable)
    flash("Contribuable supprimé.", "succes")
    return redirect(url_for("contribuables"))


# --------------------------- Dettes fiscales ---------------------------

@app.route("/dettes")
@login_required
def dettes():
    db.marquer_echues()
    return render_template("dettes.html", dettes=db.liste_dettes(), today=date.today())


@app.route("/dettes/ajouter", methods=["GET", "POST"])
@login_required
def ajouter_dette():
    if request.method == "POST":
        db.ajouter_dette(
            request.form["id_contribuable"], request.form["nature_impot"],
            request.form["montant"], request.form["date_emission"], request.form["date_echeance"],
            request.form.get("statut", "en_attente"),
        )
        flash("Créance fiscale ajoutée avec succès.", "succes")
        return redirect(url_for("dettes"))
    return render_template("dette_form.html", contribuables=db.liste_contribuables())


@app.route("/dettes/statut/<int:id_dette>/<statut>", methods=["POST"])
@login_required
def changer_statut_dette(id_dette, statut):
    if statut in ("en_attente", "echue", "relance", "mise_en_demeure", "payee"):
        db.modifier_statut_dette(id_dette, statut)
        flash("Statut du dossier mis à jour.", "succes")
    return redirect(request.referrer or url_for("dettes"))


# --------------------------- Vérification automatique des échéances ---------------------------

@app.route("/relances")
@login_required
def relances():
    db.marquer_echues()
    return render_template("relances.html", dettes_retard=db.dettes_en_retard_non_relancees(),
                            historique=db.liste_relances())


@app.route("/relances/verifier-maintenant", methods=["POST"])
@login_required
def verifier_maintenant():
    """Déclenche manuellement le moteur de relance (équivalent du job cron quotidien)."""
    verifier_et_relancer()
    flash("Vérification des échéances effectuée. Les mises en demeure nécessaires ont été générées.", "succes")
    return redirect(url_for("relances"))


# --------------------------- Notification / Mise en demeure ---------------------------

@app.route("/mise-en-demeure")
@login_required
def mise_en_demeure_index():
    db.marquer_echues()
    dettes = [d for d in db.liste_dettes() if d["statut"] in ("echue", "relance", "mise_en_demeure")]
    return render_template("mise_en_demeure_index.html", dettes=dettes)


@app.route("/mise-en-demeure/<int:id_dette>")
@login_required
def mise_en_demeure(id_dette):
    dette = db.get_dette(id_dette)
    derniere = db.derniere_relance_pour_dette(id_dette)
    return render_template("mise_en_demeure.html", dette=dette, derniere=derniere)


@app.route("/mise-en-demeure/<int:id_dette>/envoyer", methods=["POST"])
@login_required
def envoyer_mise_en_demeure(id_dette):
    dette = db.get_dette(id_dette)
    chemin_pdf = generer_mise_en_demeure(dette)

    sujet = f"Mise en demeure - Dossier D-{dette['id']:05d}"
    corps = (
        f"Bonjour {dette['nom_contribuable']},\n\n"
        f"Votre dette fiscale d'un montant de {dette['montant']} Ar est arrivée à échéance le "
        f"{dette['date_echeance']}. Veuillez procéder au règlement dans les meilleurs délais.\n\n"
        f"Cordialement,\nAdministration Fiscale"
    )
    statut_email = envoyer_email(dette.get("email"), sujet, corps)
    envoyer_sms(dette.get("telephone"), f"Relance fiscale D-{dette['id']:05d} - {dette['montant']} Ar en retard.")

    db.enregistrer_relance(id_dette, "mise_en_demeure", "email", statut_email, chemin_pdf)
    db.modifier_statut_dette(id_dette, "mise_en_demeure")

    flash("Notification envoyée (simulation) et mise en demeure générée.", "succes")
    return redirect(url_for("mise_en_demeure", id_dette=id_dette))


@app.route("/mise-en-demeure/<int:id_dette>/pdf")
@login_required
def telecharger_pdf(id_dette):
    """Génère (ou régénère) et télécharge le PDF de mise en demeure d'une dette."""
    dette = db.get_dette(id_dette)
    chemin_pdf = generer_mise_en_demeure(dette)
    return send_file(chemin_pdf, as_attachment=False)


@app.route("/mise-en-demeure/<int:id_dette>/telecharger")
@login_required
def telecharger_pdf_direct(id_dette):
    dette = db.get_dette(id_dette)
    chemin_pdf = generer_mise_en_demeure(dette)
    return send_file(chemin_pdf, as_attachment=True)


# --------------------------- Rapports ---------------------------

@app.route("/rapports")
@login_required
def rapports():
    stats = db.statistiques()
    labels_nature = [d["nature_impot"] for d in stats["par_nature"]]
    valeurs_nature = [d["nombre"] for d in stats["par_nature"]]
    return render_template(
        "rapports.html", stats=stats,
        labels_nature=json.dumps(labels_nature), valeurs_nature=json.dumps(valeurs_nature),
        statut_labels=json.dumps(["Payées", "En attente", "Échues", "Relance", "Mise en demeure"]),
        statut_valeurs=json.dumps([
            stats["par_statut"]["payee"], stats["par_statut"]["en_attente"],
            stats["par_statut"]["echue"], stats["par_statut"]["relance"],
            stats["par_statut"]["mise_en_demeure"],
        ]),
    )


# --------------------------- Paramètres ---------------------------

@app.route("/parametres")
@login_required
def parametres():
    return render_template("parametres.html")


# --------------------------- Planificateur (cron interne) ---------------------------

def demarrer_planificateur():
    scheduler = BackgroundScheduler()
    scheduler.add_job(verifier_et_relancer, "cron", hour=6, minute=0, id="verification_echeances")
    scheduler.start()


if __name__ == "__main__":
    os.makedirs(Config.DOSSIER_PDF, exist_ok=True)
    demarrer_planificateur()
    app.run(debug=True, port=5000)
