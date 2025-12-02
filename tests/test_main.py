import pytest
from datetime import date
from peewee import SqliteDatabase

# Skip cleanly if NiceGUI is not available in the environment.
pytest.importorskip("nicegui")

from database import db, ReiseModel, KategorieModel, GegenstandModel
from main import (
    _berechne_menge,
    _reisedauer_tage,
    export_reise_to_dict,
    import_reise_from_dict,
)


# Use an in-memory SQLite database for isolated tests.
test_db = SqliteDatabase(":memory:")


@pytest.fixture(autouse=True)
def _bind_test_db():
    # Bind models to the in-memory DB for each test and create fresh tables.
    with test_db.bind_ctx([ReiseModel, KategorieModel, GegenstandModel]):
        test_db.create_tables([ReiseModel, KategorieModel, GegenstandModel])
        yield
        test_db.drop_tables([ReiseModel, KategorieModel, GegenstandModel])


def test_reisedauer_tage_inclusive():
    start = date(2024, 1, 1)
    ende = date(2024, 1, 3)
    assert _reisedauer_tage(start, ende) == 3


def test_berechne_menge_mit_faktor_pro_tag():
    item = {"menge_pro_tag": 1.5}
    start = date(2024, 1, 1)
    ende = date(2024, 1, 4)
    assert _berechne_menge(item, start, ende) == 5  # 4 Tage * 1.5 gerundet


def test_berechne_menge_feste_menge():
    item = {"menge": 2}
    assert _berechne_menge(item, date(2024, 1, 1), date(2024, 1, 1)) == 2


def test_export_import_roundtrip():
    r = ReiseModel.create(
        name="Trip",
        ziel="Berlin",
        startdatum=date(2024, 1, 1),
        enddatum=date(2024, 1, 2),
        beschreibung="Test",
    )
    kat = KategorieModel.create(name="Klamotten", reise=r)
    GegenstandModel.create(name="Socken", menge=3, gepackt=True, kategorie=kat)

    data = export_reise_to_dict(r)
    imported = import_reise_from_dict(data)

    assert imported.name == "Trip"
    assert imported.kategorien.count() == 1
    imported_kat = imported.kategorien.get()
    assert imported_kat.name == "Klamotten"
    imported_item = imported_kat.gegenstaende.get()
    assert imported_item.name == "Socken"
    assert imported_item.menge == 3
    assert imported_item.gepackt is True
