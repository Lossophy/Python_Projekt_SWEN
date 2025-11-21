from datetime import datetime, date
import json
from pathlib import Path
from typing import List, Optional
from nicegui import ui, app as ng_app
import os

# Import der Datenbank-Modelle aus der separaten Datei
from database import db, ReiseModel, KategorieModel, GegenstandModel


# === Helper Funktionen ========================================================

# Wandelt einen String (YYYY-MM-DD) in ein Python date-Objekt um
def _parse_date(value: str):
    return datetime.strptime(value, "%Y-%m-%d").date()


# Gibt den Pfad zur vorlagen.json Datei zurück
def _vorlagen_datei() -> Path:
    return Path(__file__).with_name("vorlagen.json")


# Lädt die Packlisten-Vorlagen aus der JSON-Datei
def lade_vorlagen() -> List[dict]:
    pfad = _vorlagen_datei()
    if not pfad.exists():
        return []
    try:
        data = json.loads(pfad.read_text(encoding="utf-8"))
        vorlagen = data.get("vorlagen", [])
        # Sicherstellen, dass alle Felder existieren
        for v in vorlagen:
            v.setdefault("id", "")
            v.setdefault("name", "")
            v.setdefault("kategorien", [])
        return vorlagen
    except Exception:
        return []


# Sucht eine bestimmte Vorlage anhand der ID
def finde_vorlage(vorlagen: List[dict], vorlage_id: str) -> Optional[dict]:
    for v in vorlagen:
        if v.get("id") == vorlage_id:
            return v
    return None


# Berechnet die Dauer der Reise in Tagen (inklusive Starttag)
def _reisedauer_tage(start: date, ende: date) -> int:
    return max(1, (ende - start).days + 1)


# Berechnet die Menge basierend auf Reisedauer (falls konfiguriert)
def _berechne_menge(g_item: dict, start: date, ende: date) -> int:
    try:
        tage = _reisedauer_tage(start, ende)
        if "menge_pro_tag" in g_item and g_item["menge_pro_tag"] is not None:
            faktor = float(g_item.get("menge_pro_tag", 0))
            menge = int(max(1, round(tage * faktor)))
            return menge
        # Fallback: feste Menge aus der Vorlage
        menge = int(g_item.get("menge", 1))
        return max(1, menge)
    except Exception:
        return 1


# === Import / Export Logik ====================================================

# Wandelt eine Reise inkl. Kategorien und Items in ein Dictionary um (für JSON-Export)
def export_reise_to_dict(r: ReiseModel) -> dict:
    return {
        "name": r.name,
        "ziel": r.ziel,
        "startdatum": r.startdatum.isoformat(),
        "enddatum": r.enddatum.isoformat(),
        "beschreibung": r.beschreibung,
        "kategorien": [
            {
                "name": kat.name,
                "gegenstaende": [
                    {
                        "name": g.name,
                        "menge": int(g.menge),
                        "gepackt": bool(g.gepackt),
                    }
                    for g in kat.gegenstaende.order_by(GegenstandModel.id)
                ],
            }
            for kat in r.kategorien.order_by(KategorieModel.id)
        ],
    }


# Erstellt eine neue Reise aus einem Dictionary (JSON-Import)
def import_reise_from_dict(data: dict) -> ReiseModel:
    start = data.get("startdatum") or date.today().isoformat()
    ende = data.get("enddatum") or start

    r = ReiseModel.create(
        name=data.get("name", "Importierte Reise"),
        ziel=data.get("ziel", ""),
        startdatum=_parse_date(start),
        enddatum=_parse_date(ende),
        beschreibung=data.get("beschreibung", ""),
    )

    for k in data.get("kategorien", []):
        kat = KategorieModel.create(
            name=k.get("name", "Kategorie"),
            reise=r,
        )
        for g in k.get("gegenstaende", []):
            name = (g.get("name") or "").strip()
            if not name:
                continue
            menge = g.get("menge", 1)
            try:
                menge = max(1, int(menge))
            except Exception:
                menge = 1
            GegenstandModel.create(
                name=name,
                menge=menge,
                gepackt=bool(g.get("gepackt", False)),
                kategorie=kat,
            )
    return r


# === NiceGUI UI Logik =========================================================

# Öffnet die DB-Verbindung für den aktuellen Request
def _ui_db_open():
    if db.is_closed():
        db.connect(reuse_if_open=True)


# Schließt die DB-Verbindung nach dem Request
def _ui_db_close():
    if not db.is_closed():
        db.close()


# Startseite: Zeigt alle vorhandenen Reisen an
@ui.page("/")
def ui_index():
    _ui_db_open()

    # -- Header --
    with ui.header().classes("items-center justify-between px-4"):
        ui.label("🧳 PackAttack").classes("text-xl font-semibold")
        with ui.row().classes("items-center gap-3"):
            dark = ui.dark_mode()
            dark.bind_value(ng_app.storage.user, "dark_mode_enabled")
            ui.icon("light_mode").classes("text-white")
            ui.switch().bind_value(dark, "value").props("dense color=white")
            ui.icon("dark_mode").classes("text-white")

    ui.space()

    # -- Dialog: Neue Reise --
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

        # Stellt sicher, dass das Enddatum nicht vor dem Startdatum liegt
        def _sync_end_min_and_fix():
            try:
                s = date.fromisoformat(start.value)
                ende.props(f"min={s.isoformat()}")
                if date.fromisoformat(ende.value) < s:
                    ende.value = s.isoformat()
            except Exception:
                pass

        start.on_value_change(lambda e: _sync_end_min_and_fix())
        _sync_end_min_and_fix()
        beschr = ui.textarea("Beschreibung").classes("w-full")

        # Vorlagen laden
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

            # Erstellt die Reise in der DB
            def create_reise():
                try:
                    clean_name = (name.value or "").strip()
                    if not clean_name:
                        ui.notify("Bitte einen Namen für die Reise eingeben!", type="warning")
                        return

                    s = date.fromisoformat(start.value)
                    e = date.fromisoformat(ende.value)
                    if e < s:
                        ui.notify("Enddatum darf nicht vor dem Startdatum liegen.", type="warning")
                        return
                    r = ReiseModel.create(
                        name=(name.value or "").strip(),
                        ziel=(ziel.value or "").strip(),
                        startdatum=s,
                        enddatum=e,
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
                                if not kname: continue
                                krow = KategorieModel.create(name=kname, reise=r)
                                for g in kat.get("gegenstaende", []):
                                    gname = str(g.get("name", "")).strip()
                                    if not gname: continue
                                    menge = _berechne_menge(g, s, e)
                                    GegenstandModel.create(name=gname, menge=menge, kategorie=krow)

                    ui.notify(f"Reise „{r.name}“ erstellt", type="positive")
                    dlg_new.close()
                    ui.navigate.to(f"/reise/{r.id}")
                except Exception as e:
                    ui.notify(f"Fehler: {e}", type="negative")

            ui.button("Erstellen", on_click=create_reise).props(
                "outlined color=primary"
            ).style("background-color: transparent;")

    # -- Dialog: Import --
    with ui.dialog() as dlg_import, ui.card().classes("w-[520px]"):
        ui.label("Reise importieren").classes("text-lg font-semibold")
        import_area = ui.textarea("Hier den exportierten Text einfügen").classes("w-full h-64")

        def do_import():
            try:
                raw = import_area.value or ""
                data = json.loads(raw)
                new_reise = import_reise_from_dict(data)
                ui.notify(f"Reise „{new_reise.name}“ importiert", type="positive")
                dlg_import.close()
                ui.navigate.to(f"/reise/{new_reise.id}")
            except Exception as e:
                ui.notify(f"Import fehlgeschlagen: {e}", type="negative")

        with ui.row().classes("justify-end w-full mt-2"):
            ui.button("Abbrechen", on_click=dlg_import.close).props(
                "outlined color=primary"
            ).style("background-color: transparent;")
            ui.button("Importieren", on_click=do_import).props("color=primary")

    # -- Toolbar --
    with ui.row().classes("gap-3 items-center mb-2"):
        ui.button("Neue Reise", on_click=dlg_new.open).props(
            "outlined color=primary"
        ).style("background-color: transparent;")
        ui.button("Reise importieren", on_click=dlg_import.open).props(
            "outlined color=primary"
        ).style("background-color: transparent;")
        ui.button("Neu laden", on_click=lambda: refresh()).props(
            "outlined color=primary"
        ).style("background-color: transparent;")

    ui.separator()

    # -- Reisenliste --
    container = ui.column().classes("w-full gap-3 mt-3 max-w-screen-md mx-auto")

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
        with container:
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
                            ui.linear_progress(
                                value=r.fortschritt_berechnen() / 100
                            ).props("color=green").classes("my-1 w-full")
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


# Detailseite: Zeigt Kategorien und Items einer Reise
@ui.page("/reise/{reise_id}")
def ui_reise_detail(reise_id: int):
    _ui_db_open()
    r = ReiseModel.get_or_none(ReiseModel.id == reise_id)
    if not r:
        ui.label("Reise nicht gefunden").classes("text-red-600")
        _ui_db_close()
        return

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

    # --- Export / Import Dialoge ---
    with ui.dialog() as dlg_export, ui.card().classes("w-[520px]"):
        ui.label("Reise exportieren").classes("text-lg font-semibold")
        export_area = ui.textarea("Export-Daten").classes("w-full h-64")
        ui.label(
            "Text markieren, kopieren und z.B. per WhatsApp oder Mail verschicken."
        ).classes("text-sm text-gray-500 mt-1")
        with ui.row().classes("justify-end w-full mt-2"):
            ui.button("Schließen", on_click=dlg_export.close).props(
                "outlined color=primary"
            ).style("background-color: transparent;")

    with ui.dialog() as dlg_import, ui.card().classes("w-[520px]"):
        ui.label("Reise importieren").classes("text-lg font-semibold")
        import_area = ui.textarea("Hier den exportierten Text einfügen").classes("w-full h-64")

        def do_import():
            try:
                raw = import_area.value or ""
                data = json.loads(raw)
                new_reise = import_reise_from_dict(data)
                ui.notify(f"Reise „{new_reise.name}“ importiert", type="positive")
                dlg_import.close()
                ui.navigate.to(f"/reise/{new_reise.id}")
            except Exception as e:
                ui.notify(f"Import fehlgeschlagen: {e}", type="negative")

        with ui.row().classes("justify-end w-full mt-2"):
            ui.button("Abbrechen", on_click=dlg_import.close).props(
                "outlined color=primary"
            ).style("background-color: transparent;")
            ui.button("Importieren", on_click=do_import).props("color=primary")

    def open_export():
        r_current = ReiseModel.get_by_id(reise_id)
        data = export_reise_to_dict(r_current)
        export_area.value = json.dumps(data, ensure_ascii=False, indent=2)
        dlg_export.open()

    with ui.row().classes("gap-2 mt-2 max-w-screen-md mx-auto"):
        ui.button("Reise exportieren", on_click=open_export).props(
            "outlined color=primary"
        ).style("background-color: transparent;")

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

    # Confirm-Dialog
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

    # Item Logik
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
        if total == 0: return 0.0
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

                    # Items
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
                                    ui.button(icon="remove", on_click=lambda iid=it.id: update_menge(iid, -1)).props("flat round dense")
                                    ui.label(f"× {int(it.menge)}").classes("w-10 text-center")
                                    ui.button(icon="add", on_click=lambda iid=it.id: update_menge(iid, +1)).props("flat round dense")
                            ui.button(
                                icon="delete",
                                on_click=lambda iid=it.id: confirm_delete(lambda: delete_item(iid), text=f"„{it.name}“ löschen?"),
                            ).props("flat round dense")

                    # Neues Item
                    with ui.row().classes("mt-2 items-end"):
                        new_name = ui.input("Neuer Gegenstand").classes("w-64")
                        new_menge = ui.number("Menge", value=1, min=1, format="%d").classes("w-32")
                        ui.button(
                            "Hinzufügen",
                            on_click=lambda k=kat, nn=new_name, nm=new_menge: add_item(
                                k, nn.value or "", int(nm.value or 1)
                            ),
                        ).props("outlined color=primary").style("background-color: transparent;")

    refresh()
    _ui_db_close()


# === App-Start ================================================================

# Datenbank-Tabellen einmalig beim Start erstellen (falls nicht vorhanden)
db.connect(reuse_if_open=True)
db.create_tables([ReiseModel, KategorieModel, GegenstandModel])
db.close()

if __name__ in {"__main__", "__mp_main__"}:
    ui.run(
        reload=True,
        title="PackAttack",
        storage_secret=os.getenv("NICEGUI_STORAGE_SECRET", "change-me-please-31+chars"),
        tailwind={
            "theme": {
                "extend": {
                    "colors": {
                        "primary": "#5898d4",
                    }
                }
            }
        },
    )