from datetime import datetime
from typing import List

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    url_for,
    abort,
)
from peewee import (
    Model,
    SqliteDatabase,
    AutoField,
    CharField,
    DateField,
    TextField,
    IntegerField,
    BooleanField,
    ForeignKeyField,
)


app = Flask(__name__)

# Peewee database setup
db = SqliteDatabase("app.db", pragmas={"foreign_keys": 1})


@app.before_request
def _db_connect():
    if db.is_closed():
        db.connect(reuse_if_open=True)


@app.teardown_request
def _db_close(exception=None):
    if not db.is_closed():
        db.close()


def _parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


class BaseModel(Model):
    class Meta:
        database = db


class ReiseModel(BaseModel):
    class Meta:
        table_name = "reisen"
    id = AutoField()
    name = CharField(max_length=200)
    startdatum = DateField()
    enddatum = DateField()
    beschreibung = TextField(default="")

    def fortschritt_berechnen(self) -> float:
        total = sum(len(k.gegenstaende) for k in self.kategorien)
        if total == 0:
            return 0.0
        gepackt = sum(
            sum(1 for g in k.gegenstaende if g.gepackt) for k in self.kategorien
        )
        return round(gepackt / total * 100.0, 2)


class KategorieModel(BaseModel):
    class Meta:
        table_name = "kategorien"
    id = AutoField()
    name = CharField(max_length=200)
    reise = ForeignKeyField(ReiseModel, backref="kategorien", on_delete="CASCADE")

    def anzahl_gepackt(self) -> int:
        return sum(1 for g in self.gegenstaende if g.gepackt)

    def anzahl_gesamt(self) -> int:
        return len(self.gegenstaende)


class GegenstandModel(BaseModel):
    class Meta:
        table_name = "gegenstaende"
    id = AutoField()
    name = CharField(max_length=200)
    menge = IntegerField(default=1)
    gepackt = BooleanField(default=False)
    kategorie = ForeignKeyField(KategorieModel, backref="gegenstaende", on_delete="CASCADE")


@app.get("/")
def index():
    reisen: List[ReiseModel] = list(ReiseModel.select().order_by(ReiseModel.id))
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

    r = ReiseModel.create(
        name=name,
        startdatum=_parse_date(start),
        enddatum=_parse_date(ende),
        beschreibung=beschreibung,
    )
    return redirect(url_for("reise_detail", reise_id=r.id))


@app.get("/reise/<int:reise_id>")
def reise_detail(reise_id: int):
    r = ReiseModel.get_or_none(ReiseModel.id == reise_id)
    if not r:
        abort(404)
    return render_template("reise_detail.html", reise_id=reise_id, reise=r)


@app.post("/reise/<int:reise_id>/kategorie")
def kategorie_hinzufuegen(reise_id: int):
    r = ReiseModel.get_or_none(ReiseModel.id == reise_id)
    if not r:
        abort(404)
    name = request.form.get("kategorie_name", "").strip()
    if name:
        KategorieModel.create(name=name, reise=r)
    return redirect(url_for("reise_detail", reise_id=reise_id))


@app.post("/reise/<int:reise_id>/gegenstand")
def gegenstand_hinzufuegen(reise_id: int):
    r = ReiseModel.get_or_none(ReiseModel.id == reise_id)
    if not r:
        abort(404)
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
    kategorien = list(r.kategorien.order_by(KategorieModel.id))
    if name and 0 <= kat_index < len(kategorien):
        kat = kategorien[kat_index]
        GegenstandModel.create(name=name, menge=menge, kategorie=kat)
    return redirect(url_for("reise_detail", reise_id=reise_id))


@app.post("/reise/<int:reise_id>/toggle/<int:kat_index>/<int:item_index>")
def toggle_gepackt(reise_id: int, kat_index: int, item_index: int):
    r = ReiseModel.get_or_none(ReiseModel.id == reise_id)
    if not r:
        abort(404)
    kategorien = list(r.kategorien.order_by(KategorieModel.id))
    if 0 <= kat_index < len(kategorien):
        kat = kategorien[kat_index]
        items = list(kat.gegenstaende.order_by(GegenstandModel.id))
        if 0 <= item_index < len(items):
            item = items[item_index]
            item.gepackt = not item.gepackt
            item.save()
    return redirect(url_for("reise_detail", reise_id=reise_id))


with app.app_context():
    db.connect(reuse_if_open=True)
    db.create_tables([ReiseModel, KategorieModel, GegenstandModel])
    db.close()


if __name__ == "__main__":
    app.run(debug=True)
