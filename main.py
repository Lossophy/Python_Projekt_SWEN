from datetime import datetime
from typing import List

from flask import Flask, redirect, render_template, request, url_for
from flask_sqlalchemy import SQLAlchemy


app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///app.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


def _parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


class ReiseModel(db.Model):
    __tablename__ = "reisen"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    startdatum = db.Column(db.Date, nullable=False)
    enddatum = db.Column(db.Date, nullable=False)
    beschreibung = db.Column(db.Text, default="")

    kategorien = db.relationship(
        "KategorieModel",
        backref="reise",
        cascade="all, delete-orphan",
        order_by="KategorieModel.id",
    )

    def fortschritt_berechnen(self) -> float:
        total = sum(len(k.gegenstaende) for k in self.kategorien)
        if total == 0:
            return 0.0
        gepackt = sum(sum(1 for g in k.gegenstaende if g.gepackt) for k in self.kategorien)
        return round(gepackt / total * 100.0, 2)


class KategorieModel(db.Model):
    __tablename__ = "kategorien"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    reise_id = db.Column(db.Integer, db.ForeignKey("reisen.id"), nullable=False)

    gegenstaende = db.relationship(
        "GegenstandModel",
        backref="kategorie",
        cascade="all, delete-orphan",
        order_by="GegenstandModel.id",
    )

    def anzahl_gepackt(self) -> int:
        return sum(1 for g in self.gegenstaende if g.gepackt)

    def anzahl_gesamt(self) -> int:
        return len(self.gegenstaende)


class GegenstandModel(db.Model):
    __tablename__ = "gegenstaende"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    menge = db.Column(db.Integer, default=1)
    gepackt = db.Column(db.Boolean, default=False)
    kategorie_id = db.Column(db.Integer, db.ForeignKey("kategorien.id"), nullable=False)


@app.get("/")
def index():
    reisen: List[ReiseModel] = ReiseModel.query.order_by(ReiseModel.id).all()
    return render_template("index.html", reisen=reisen)


@app.get("/reise/neu")
def reise_neu_form():
    return render_template("reise_form.html")


@app.post("/reise/neu")
def reise_neu_submit():
    name = request.form.get("name", "").strip()
    start = request.form.get("startdatum", "").strip()
    ende = request.form.get("enddatum", "").strip()
    beschreibung = request.form.get("beschreibung", "").strip()

    if not name or not start or not ende:
        return render_template(
            "reise_form.html",
            error="Bitte Name, Start- und Enddatum angeben.",
            form={
                "name": name,
                "startdatum": start,
                "enddatum": ende,
                "beschreibung": beschreibung,
            },
        )

    r = ReiseModel(
        name=name,
        startdatum=_parse_date(start),
        enddatum=_parse_date(ende),
        beschreibung=beschreibung,
    )
    db.session.add(r)
    db.session.commit()
    return redirect(url_for("reise_detail", reise_id=r.id))


@app.get("/reise/<int:reise_id>")
def reise_detail(reise_id: int):
    r = ReiseModel.query.get_or_404(reise_id)
    return render_template("reise_detail.html", reise_id=reise_id, reise=r)


@app.post("/reise/<int:reise_id>/kategorie")
def kategorie_hinzufuegen(reise_id: int):
    r = ReiseModel.query.get_or_404(reise_id)
    name = request.form.get("kategorie_name", "").strip()
    if name:
        db.session.add(KategorieModel(name=name, reise=r))
        db.session.commit()
    return redirect(url_for("reise_detail", reise_id=reise_id))


@app.post("/reise/<int:reise_id>/gegenstand")
def gegenstand_hinzufuegen(reise_id: int):
    r = ReiseModel.query.get_or_404(reise_id)
    name = request.form.get("gegenstand_name", "").strip()
    menge_raw = request.form.get("menge", "1").strip()
    kat_index_raw = request.form.get("kategorie_index", "").strip()
    try:
        menge = max(1, int(menge_raw))
    except ValueError:
        menge = 1
    try:
        kat_index = int(kat_index_raw)
    except ValueError:
        kat_index = -1
    kategorien = list(r.kategorien)
    if name and 0 <= kat_index < len(kategorien):
        kat = kategorien[kat_index]
        db.session.add(GegenstandModel(name=name, menge=menge, kategorie=kat))
        db.session.commit()
    return redirect(url_for("reise_detail", reise_id=reise_id))


@app.post("/reise/<int:reise_id>/toggle/<int:kat_index>/<int:item_index>")
def toggle_gepackt(reise_id: int, kat_index: int, item_index: int):
    r = ReiseModel.query.get_or_404(reise_id)
    kategorien = list(r.kategorien)
    if 0 <= kat_index < len(kategorien):
        kat = kategorien[kat_index]
        items = list(kat.gegenstaende)
        if 0 <= item_index < len(items):
            g = items[item_index]
            g.gepackt = not g.gepackt
            db.session.commit()
    return redirect(url_for("reise_detail", reise_id=reise_id))


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)

