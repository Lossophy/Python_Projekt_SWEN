from datetime import datetime
from typing import Dict

from flask import Flask, redirect, render_template, request, url_for

from backend import Gegenstand, Kategorie, Reise


app = Flask(__name__)


# Sehr einfaches In-Memory-"Repository" für das Grundgerüst
# Key: int ID, Value: Reise
_reisen: Dict[int, Reise] = {}
_next_id: int = 1


def _parse_date(value: str) -> datetime.date:
    return datetime.strptime(value, "%Y-%m-%d").date()


@app.get("/")
def index():
    # Liste aller Reisen mit Fortschritt
    return render_template("index.html", reisen=_reisen)


@app.get("/reise/neu")
def reise_neu_form():
    return render_template("reise_form.html")


@app.post("/reise/neu")
def reise_neu_submit():
    global _next_id
    name = request.form.get("name", "").strip()
    start = request.form.get("startdatum", "").strip()
    ende = request.form.get("enddatum", "").strip()
    beschreibung = request.form.get("beschreibung", "").strip()

    if not name or not start or not ende:
        # Minimale Validierung
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

    r = Reise(
        name=name,
        startdatum=_parse_date(start),
        enddatum=_parse_date(ende),
        beschreibung=beschreibung,
    )
    _reisen[_next_id] = r
    rid = _next_id
    _next_id += 1
    return redirect(url_for("reise_detail", reise_id=rid))


@app.get("/reise/<int:reise_id>")
def reise_detail(reise_id: int):
    r = _reisen.get(reise_id)
    if not r:
        return render_template("not_found.html"), 404
    return render_template("reise_detail.html", reise_id=reise_id, reise=r)


@app.post("/reise/<int:reise_id>/kategorie")
def kategorie_hinzufuegen(reise_id: int):
    r = _reisen.get(reise_id)
    if not r:
        return render_template("not_found.html"), 404
    name = request.form.get("kategorie_name", "").strip()
    if name:
        r.kategorie_hinzufuegen(Kategorie(name))
    return redirect(url_for("reise_detail", reise_id=reise_id))


@app.post("/reise/<int:reise_id>/gegenstand")
def gegenstand_hinzufuegen(reise_id: int):
    r = _reisen.get(reise_id)
    if not r:
        return render_template("not_found.html"), 404
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
    if name and 0 <= kat_index < len(r.kategorien):
        r.kategorien[kat_index].gegenstand_hinzufuegen(
            Gegenstand(name=name, menge=menge)
        )
    return redirect(url_for("reise_detail", reise_id=reise_id))


@app.post("/reise/<int:reise_id>/toggle/<int:kat_index>/<int:item_index>")
def toggle_gepackt(reise_id: int, kat_index: int, item_index: int):
    r = _reisen.get(reise_id)
    if not r:
        return render_template("not_found.html"), 404
    if 0 <= kat_index < len(r.kategorien):
        kat = r.kategorien[kat_index]
        if 0 <= item_index < len(kat.gegenstaende):
            g = kat.gegenstaende[item_index]
            g.gepackt = not g.gepackt
    return redirect(url_for("reise_detail", reise_id=reise_id))


if __name__ == "__main__":
    # Debug nur fürs Grundgerüst; für Produktion entfernen/ändern
    app.run(debug=True)
