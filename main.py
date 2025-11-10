from datetime import datetime, date
import json
from pathlib import Path
from typing import List, Optional

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    url_for,
    abort,
)
from nicegui import ui, app as ng_app
import os


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

# === UI-Schalter ==============================================================
# True  -> NiceGUI (Browser-UI auf Port 8080)
# False -> klassische Flask-Templates (Port 5000)
USE_NICEGUI = True

# === Flask-App ================================================================

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


def _vorlagen_datei() -> Path:
    return Path(__file__).with_name("vorlagen.json")


def lade_vorlagen() -> List[dict]:
    pfad = _vorlagen_datei()
    if not pfad.exists():
        return []
    try:
        data = json.loads(pfad.read_text(encoding="utf-8"))
        vorlagen = data.get("vorlagen", [])
        # normalize structure a bit
        for v in vorlagen:
            v.setdefault("id", "")
            v.setdefault("name", "")
            v.setdefault("kategorien", [])
        return vorlagen
    except Exception:
        # On parse error, return no templates rather than crashing the form
        return []


def finde_vorlage(vorlagen: List[dict], vorlage_id: str) -> Optional[dict]:
    for v in vorlagen:
        if v.get("id") == vorlage_id:
            return v
    return None


def _reisedauer_tage(start: date, ende: date) -> int:
    return max(1, (ende - start).days + 1)


# Zusammenhang zwischen Reisetagen und empfohlener Menge
def _berechne_menge(g_item: dict, start: date, ende: date) -> int:
    try:
        tage = _reisedauer_tage(start, ende)
        if "menge_pro_tag" in g_item and g_item["menge_pro_tag"] is not None:
            faktor = float(g_item.get("menge_pro_tag", 0))
            menge = int(max(1, round(tage * faktor)))
            return menge
        # Fallback: feste Menge
        menge = int(g_item.get("menge", 1))
        return max(1, menge)
    except Exception:
        return 1


class BaseModel(Model):
    class Meta:
        database = db


class ReiseModel(BaseModel):
    class Meta:
        table_name = "reisen"

    id = AutoField()
    name = CharField(max_length=200)
    ziel = CharField(max_length=200)
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
    kategorie = ForeignKeyField(
        KategorieModel, backref="gegenstaende", on_delete="CASCADE"
    )


# === Flask-Routen (bestehend) ================================================


@app.get("/")
def index():
    reisen: List[ReiseModel] = list(ReiseModel.select().order_by(ReiseModel.id))
    return render_template("index.html", reisen=reisen)


@app.get("/reise/neu")
def reise_neu_form():
    return render_template("reise_form.html", vorlagen=lade_vorlagen(), form=None)


@app.post("/reise/neu")
def reise_neu_submit():
    name = request.form.get("name", "").strip()
    ziel = request.form.get("ziel", "").strip()
    start = request.form.get("startdatum", "").strip()
    ende = request.form.get("enddatum", "").strip()
    beschreibung = request.form.get("beschreibung", "").strip()
    vorlage_id = request.form.get("vorlage_id", "").strip()

    if not name or not start or not ende:
        return render_template(
            "reise_form.html",
            error="Bitte Name, Start- und Enddatum angeben.",
            form={
                "name": name,
                "ziel": ziel,
                "startdatum": start,
                "enddatum": ende,
                "beschreibung": beschreibung,
                "vorlage_id": vorlage_id,
            },
            vorlagen=lade_vorlagen(),
        )
    s = _parse_date(start)
    e = _parse_date(ende)

    if e < s:
        return render_template(
            "reise_form.html",
            error="Enddatum darf nicht vor dem Startdatum liegen.",
            form={
                "name": name,
                "ziel": ziel,
                "startdatum": start,
                "enddatum": ende,
                "beschreibung": beschreibung,
                "vorlage_id": vorlage_id,
            },
            vorlagen=lade_vorlagen(),
        )

    r = ReiseModel.create(
        name=name,
        ziel=ziel,
        startdatum=_parse_date(start),
        enddatum=_parse_date(ende),
        beschreibung=beschreibung,
    )

    # Falls Vorlage ausgewählt, Kategorien + Gegenstände anlegen
    if vorlage_id:
        vorlagen = lade_vorlagen()
        vorlage = finde_vorlage(vorlagen, vorlage_id)
        if vorlage:
            for kat in vorlage.get("kategorien", []):
                kat_name = str(kat.get("name", "")).strip()
                if not kat_name:
                    continue
                kat_row = KategorieModel.create(name=kat_name, reise=r)
                for g in kat.get("gegenstaende", []):
                    g_name = str(g.get("name", "")).strip()
                    if not g_name:
                        continue
                    menge = _berechne_menge(g, s, e)
                    GegenstandModel.create(name=g_name, menge=menge, kategorie=kat_row)
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
    kat_id_raw = request.form.get("kategorie_id", "").strip()
    try:
        kat_id = int(kat_id_raw)
    except ValueError:
        kat_id = -1

    name = request.form.get(f"gegenstand_name_{kat_id}", "").strip()
    menge_raw = request.form.get(f"menge_{kat_id}", "1").strip()
    try:
        menge = max(1, int(menge_raw))
    except ValueError:
        menge = 1

    if name and kat_id > 0:
        kat = KategorieModel.get_or_none(
            KategorieModel.id == kat_id, KategorieModel.reise == r
        )
        if kat:
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


# === NiceGUI-UI (zusätzlich, optional via USE_NICEGUI) ========================
def _ui_db_open():
    if db.is_closed():
        db.connect(reuse_if_open=True)


def _ui_db_close():
    if not db.is_closed():
        db.close()


def _reisen_laden():
    return list(ReiseModel.select().order_by(ReiseModel.id))


@ui.page("/")
def ui_index():
    _ui_db_open()

    # -- Header ----------------------------------------------------------------
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("🧳 PackAttack").classes("text-xl font-semibold")
        with ui.row().classes("items-center gap-3"):
            dark = ui.dark_mode()
            dark.bind_value(ng_app.storage.user, "dark_mode_enabled")
            ui.icon("light_mode").classes("text-white")
            ui.switch().bind_value(dark, "value").props("dense color=white")
            ui.icon("dark_mode").classes("text-white")

    ui.space()

    # -- Dialog: Neue Reise -----------------------------------------------------
    with ui.dialog() as dlg_new, ui.card().classes("w-[520px]"):
        ui.label("Neue Reise anlegen").classes("text-lg font-semibold")
        name = (
            ui.input("Name der Reise")
            .props("autofocus clearable")
            .classes("w-full")
            .props("label-color=grey")
        )
        ziel = (
            ui.input("Zielort")
            .props("clearable")
            .classes("w-full")
            .props("label-color=grey")
        )
        with ui.row().classes("w-full"):
            start = ui.date(value=str(date.today())).classes("flex-1")
            ende = ui.date(value=str(date.today())).classes("flex-1")

        def _sync_end_min_and_fix():
            try:
                s = date.fromisoformat(start.value)
                ende.props(f"min={s.isoformat()}")
                # falls Ende < Start gewählt wurde, automatisch auf Start setzen
                if date.fromisoformat(ende.value) < s:
                    ende.value = s.isoformat()
            except Exception:
                pass

        start.on_value_change(lambda e: _sync_end_min_and_fix())
        _sync_end_min_and_fix()
        beschr = ui.textarea("Beschreibung").classes("w-full")

        # Vorlagen-Auswahl (Namen anzeigen, ID intern auflösen)
        vorlagen = lade_vorlagen()
        name_to_id = {
            v.get("name", f"Vorlage {i+1}"): v.get("id", "")
            for i, v in enumerate(vorlagen)
        }
        select_vorlage = ui.select(
            options=list(name_to_id.keys()), label="Vorlage (optional)"
        ).props("clearable")

        with ui.row().classes("justify-end w-full mt-2"):
            ui.button("Abbrechen", on_click=dlg_new.close).props(
                "outlined color=primary"
            ).style("background-color: transparent;")

            def create_reise():
                try:
                    s = date.fromisoformat(start.value)
                    e = date.fromisoformat(ende.value)
                    if e < s:
                        ui.notify(
                            "Enddatum darf nicht vor dem Startdatum liegen.",
                            type="warning",
                        )
                        return
                    r = ReiseModel.create(
                        name=(name.value or "").strip(),
                        ziel=(ziel.value or "").strip(),
                        startdatum=date.fromisoformat(start.value),
                        enddatum=date.fromisoformat(ende.value),
                        beschreibung=beschr.value or "",
                    )
                    # Falls Vorlage gewählt, Kategorien + Items anlegen
                    chosen = select_vorlage.value
                    if chosen:
                        vorlage_id = name_to_id.get(chosen, "")
                        v = finde_vorlage(vorlagen, vorlage_id)
                        if v:
                            for kat in v.get("kategorien", []):
                                kname = str(kat.get("name", "")).strip()
                                if not kname:
                                    continue
                                krow = KategorieModel.create(name=kname, reise=r)
                                for g in kat.get("gegenstaende", []):
                                    gname = str(g.get("name", "")).strip()
                                    if not gname:
                                        continue
                                    menge = _berechne_menge(g, s, e)
                                    GegenstandModel.create(
                                        name=gname, menge=menge, kategorie=krow
                                    )

                    ui.notify(f"Reise „{r.name}“ erstellt", type="positive")
                    dlg_new.close()
                    ui.navigate(f"/reise/{r.id}")
                except Exception as e:
                    ui.notify(f"Fehler: {e}", type="negative")

            ui.button("Erstellen", on_click=create_reise).props(
                "outlined color=primary"
            ).style("background-color: transparent;")

    # -- Toolbar ----------------------------------------------------------------
    with ui.row().classes("gap-3 items-center mb-2"):
        # Button 1: Neue Reise (Outline-Stil: Rand und Text in #5898d4)
        ui.button("Neue Reise", on_click=dlg_new.open).props(
            "outlined color=primary"
        ).style("background-color: transparent;")
        # Button 2: Neu laden (Outline-Stil: Rand und Text in #5898d4)
        ui.button("Neu laden", on_click=lambda: refresh()).props(
            "outlined color=primary"
        ).style("background-color: transparent;")

    ui.separator()

    # -- Reisenliste ------------------------------------------------------------
    container = ui.column().classes("w-full gap-3 mt-3 max-w-screen-md mx-auto")

    # Bestätigungsdialog fürs Löschen
    with ui.dialog() as dlg_confirm, ui.card():
        confirm_msg = ui.label("Sicher löschen?")
        with ui.row().classes("justify-end w-full mt-2"):
            ui.button("Abbrechen", on_click=dlg_confirm.close).props(
                "outlined color=primary"
            ).style("background-color: transparent;")
            btn_yes = ui.button("Löschen").props("color=negative")

    def confirm_delete(fn, text="Sicher löschen?"):
        confirm_msg.text = text

        btn_yes.clear()

        btn_yes.on("click", lambda: (dlg_confirm.close(), fn()))
        dlg_confirm.open()

    def delete_reise_by_id(rid: int):
        try:
            ReiseModel.delete_by_id(rid)
            ui.notify("Reise gelöscht", type="warning")
            refresh()
        except Exception as e:
            ui.notify(f"Fehler: {e}", type="negative")

    def card_for_reise(r: ReiseModel):
        with ui.card().classes("w-full"):
            with ui.row().classes("items-start justify-between w-full"):
                with ui.column().classes("gap-1"):
                    ui.link(r.name, f"/reise/{r.id}").classes(
                        "text-lg font-semibold text-primary"
                    ).style("text-decoration: none;")
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("event").classes("opacity-70")
                        ui.label(
                            f"{r.startdatum.strftime('%d.%m.%Y')} – {r.enddatum.strftime('%d.%m.%Y')}"
                        )
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("task_alt").classes("opacity-70")
                        ui.linear_progress(value=r.fortschritt_berechnen() / 100).props(
                            "color=green"
                        ).classes("my-1 w-full")
                        ui.label(f"Fortschritt: {r.fortschritt_berechnen()} %")
                ui.button(
                    icon="delete",
                    on_click=lambda rid=r.id: confirm_delete(
                        lambda: delete_reise_by_id(rid),
                        text=f"Reise „{r.name}“ wirklich löschen?",
                    ),
                ).props("flat round")

    def refresh():
        container.clear()
        for r in ReiseModel.select().order_by(ReiseModel.id):
            card_for_reise(r)

    refresh()
    _ui_db_close()


@ui.page("/reise/{reise_id}")
def ui_reise_detail(reise_id: int):
    _ui_db_open()
    r = ReiseModel.get_or_none(ReiseModel.id == reise_id)
    if not r:
        ui.label("Reise nicht gefunden").classes("text-red-600")
        _ui_db_close()
        return

    # Dark-Mode auch hier aus dem persistenten Speicher holen
    dark = ui.dark_mode()
    dark.bind_value(ng_app.storage.user, "dark_mode_enabled")

    # Header
    with ui.header().classes("items-center justify-between px-4 text-white").style(
        "background-color: primary;"
    ):
        ui.link("← Zur Übersicht", "/").classes("text-white")
        ui.label(f"🔖 {r.name}").classes("text-lg font-semibold")

    with ui.row().classes("items-center gap-3 mt-2"):
        ui.icon("event").classes("opacity-70")
        ui.label(
            f"{r.startdatum.strftime('%d.%m.%Y')} – {r.enddatum.strftime('%d.%m.%Y')}"
        )

    prog = (
        ui.linear_progress(value=r.fortschritt_berechnen() / 100)
        .props("color=green")
        .classes("my-2")
    )
    ui.separator()

    # Kategorie anlegen
    with ui.expansion("Kategorie hinzufügen").classes("w-full max-w-screen-md mx-auto"):
        kat_name = ui.input("Kategoriename").classes("w-full")

        def add_kat():
            if kat_name.value and kat_name.value.strip():
                KategorieModel.create(name=kat_name.value.strip(), reise=r)
                kat_name.value = ""
                ui.notify("Kategorie erstellt", type="positive")
                refresh()

        ui.button("Hinzufügen", on_click=add_kat).props("outlined color=primary").style(
            "background-color: transparent;"
        )

    container = ui.column().classes("w-full mt-2 max-w-screen-md mx-auto")

    # Confirm-Dialog fürs Item-Löschen
    with ui.dialog() as dlg_confirm, ui.card():
        confirm_msg = ui.label("Sicher löschen?")
        with ui.row().classes("justify-end w-full mt-2"):
            ui.button("Abbrechen", on_click=dlg_confirm.close).props(
                "outlined color=primary"
            ).style("background-color: transparent;")
            btn_yes = ui.button("Löschen").props("color=negative")

    def confirm_delete(fn, text="Sicher löschen?"):
        confirm_msg.text = text

        def set_yes():
            dlg_confirm.close()
            fn()

        btn_yes.on("click", set_yes)
        dlg_confirm.open()

    def update_menge(item_id: int, delta: int):
        it = GegenstandModel.get_or_none(GegenstandModel.id == item_id)
        if it:
            it.menge = max(1, int(it.menge) + int(delta))
            it.save()
            refresh()

    def toggle_item(item_id: int, cb):
        it = GegenstandModel.get_or_none(GegenstandModel.id == item_id)
        if it:
            it.gepackt = bool(cb.value)
            it.save()
            refresh()

    def delete_item(item_id: int):
        GegenstandModel.delete_by_id(item_id)
        refresh()

    def delete_category(kat_id: int):
        KategorieModel.delete_by_id(kat_id)
        refresh()

    def add_item(kat: "KategorieModel", name: str, menge: int):
        if name.strip():
            GegenstandModel.create(
                name=name.strip(), menge=max(1, int(menge)), kategorie=kat
            )
            ui.notify("Gegenstand hinzugefügt", type="positive")
            refresh()

    def kat_progress(kat: KategorieModel) -> float:
        total = kat.anzahl_gesamt()
        if total == 0:
            return 0.0
        return round(kat.anzahl_gepackt() / total, 2)

    def refresh():
        container.clear()
        r_ref = ReiseModel.get_by_id(reise_id)
        prog.value = r_ref.fortschritt_berechnen() / 100

        for kat in r_ref.kategorien.order_by(KategorieModel.id):
            with container:
                with ui.card().classes("w-full"):
                    with ui.row().classes("items-center justify-between"):
                        ui.label(kat.name).classes("text-lg font-semibold")

                        ui.button(
                            icon="delete",
                            on_click=lambda k_id=kat.id, k_name=kat.name: confirm_delete(
                                lambda: delete_category(k_id),
                                text=f"Kategorie „{k_name}“ wirklich löschen?",
                            ),
                        ).props("flat round dense")
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("task_alt").classes("opacity-70")
                            ui.label(f"{kat.anzahl_gepackt()}/{kat.anzahl_gesamt()}")
                    ui.linear_progress(value=kat_progress(kat)).props("outlined").style(
                        f"background-color: transparent; border-color: #5898d4; color: #5898d4;"
                    ).classes("my-1")

                    # Items (Zeilen)
                    for it in kat.gegenstaende.order_by(GegenstandModel.id):
                        with ui.row().classes("items-center justify-between w-full"):
                            with ui.row().classes("items-center gap-3"):
                                ui.checkbox(
                                    value=bool(it.gepackt),
                                    on_change=lambda e, item_id=it.id: toggle_item(
                                        item_id, e.sender
                                    ),
                                )
                                ui.label(it.name).classes("min-w-[160px]")
                                with ui.row().classes("items-center gap-1"):
                                    ui.button(
                                        icon="remove",
                                        on_click=lambda iid=it.id: update_menge(
                                            iid, -1
                                        ),
                                    ).props("flat round dense")
                                    ui.label(f"× {int(it.menge)}").classes(
                                        "w-10 text-center"
                                    )
                                    ui.button(
                                        icon="add",
                                        on_click=lambda iid=it.id: update_menge(
                                            iid, +1
                                        ),
                                    ).props("flat round dense")

                            ui.button(
                                icon="delete",
                                on_click=lambda iid=it.id: confirm_delete(
                                    lambda: delete_item(iid),
                                    text=f"„{it.name}“ löschen?",
                                ),
                            ).props("flat round dense")

                    # Neues Item hinzufügen
                    with ui.row().classes("mt-2 items-end"):
                        new_name = ui.input("Neuer Gegenstand").classes("w-64")
                        new_menge = ui.number(
                            "Menge", value=1, min=1, format="%d"
                        ).classes("w-32")
                        ui.button(
                            "Hinzufügen",
                            # Ohne k=kat, nn=new_name,... würde jeder "Hinzufügen"-Button versuchen, nur in die unterste Kategorie einzufügen.
                            on_click=lambda k=kat, nn=new_name, nm=new_menge: add_item(
                                k, nn.value or "", int(nm.value or 1)
                            ),
                        ).props("outlined color=primary").style(
                            "background-color: transparent;"
                        )

    refresh()
    _ui_db_close()


# === App-Start ================================================================
with app.app_context():
    db.connect(reuse_if_open=True)
    db.create_tables([ReiseModel, KategorieModel, GegenstandModel])
    db.close()

if __name__ in {"__main__", "__mp_main__"}:
    if USE_NICEGUI:
        # Optional: Flask unter /flask mounten, um alte Routen parallel zu sehen
        # nicegui_app.mount('/flask', WSGIMiddleware(app))
        ui.run(
            reload=True,
            title="PackAttack (NiceGUI)",
            storage_secret=os.getenv(
                "NICEGUI_STORAGE_SECRET", "change-me-please-31+chars"
            ),
            tailwind={
                "theme": {
                    "extend": {
                        "colors": {
                            "primary": "#5898d4",
                        }
                    }
                }
            },
        )  # -> http://127.0.0.1:8080/
    else:
        app.run(debug=True)  # -> http://127.0.0.1:5000/
