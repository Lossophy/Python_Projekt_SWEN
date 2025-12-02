import sys
import json
import importlib.util
import unittest
from unittest import mock
from pathlib import Path
from datetime import date
from tempfile import NamedTemporaryFile
from peewee import SqliteDatabase

# Ensure project root is on the import path for test runs.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Skip cleanly if NiceGUI (dependency of main.py) is not available in the environment.
NICEGUI_AVAILABLE = importlib.util.find_spec("nicegui") is not None
if NICEGUI_AVAILABLE:
    from main import (
        _berechne_menge,
        _reisedauer_tage,
        _parse_date,
        _vorlagen_datei,
        lade_vorlagen,
        finde_vorlage,
        export_reise_to_dict,
        import_reise_from_dict,
    )
else:
    # Raise SkipTest at import time so unittest discovery still registers the module.
    raise unittest.SkipTest("NiceGUI not installed; skipping PackAttack tests.")

from database import db, ReiseModel, KategorieModel, GegenstandModel


# Use an in-memory SQLite database for isolated tests.
test_db = SqliteDatabase(":memory:", pragmas={"foreign_keys": 1})


@unittest.skipUnless(NICEGUI_AVAILABLE, "NiceGUI not installed")
class TestPackAttack(unittest.TestCase):
    def setUp(self):
        # Bind models to the in-memory DB for each test, connect, and create fresh tables.
        self._ctx = test_db.bind_ctx([ReiseModel, KategorieModel, GegenstandModel])
        self._ctx.__enter__()
        test_db.connect(reuse_if_open=True)
        test_db.create_tables([ReiseModel, KategorieModel, GegenstandModel])

    def tearDown(self):
        test_db.drop_tables([ReiseModel, KategorieModel, GegenstandModel])
        test_db.close()
        self._ctx.__exit__(None, None, None)

    def test_reisedauer_tage_inclusive(self):
        start = date(2024, 1, 1)
        ende = date(2024, 1, 3)
        self.assertEqual(_reisedauer_tage(start, ende), 3)

    def test_berechne_menge_mit_faktor_pro_tag(self):
        item = {"menge_pro_tag": 1.5}
        start = date(2024, 1, 1)
        ende = date(2024, 1, 4)
        self.assertEqual(_berechne_menge(item, start, ende), 5)  # 4 Tage * 1.5 gerundet

    def test_berechne_menge_feste_menge(self):
        item = {"menge": 2}
        self.assertEqual(_berechne_menge(item, date(2024, 1, 1), date(2024, 1, 1)), 2)

    def test_export_import_roundtrip(self):
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

        self.assertEqual(imported.name, "Trip")
        self.assertEqual(imported.kategorien.count(), 1)
        imported_kat = imported.kategorien.get()
        self.assertEqual(imported_kat.name, "Klamotten")
        imported_item = imported_kat.gegenstaende.get()
        self.assertEqual(imported_item.name, "Socken")
        self.assertEqual(imported_item.menge, 3)
        self.assertTrue(imported_item.gepackt)

    def test_parse_date_valid_and_invalid(self):
        self.assertEqual(_parse_date("2024-05-10"), date(2024, 5, 10))
        with self.assertRaises(ValueError):
            _parse_date("10.05.2024")

    def test_lade_vorlagen_from_temp_file(self):
        payload = {
            "vorlagen": [
                {
                    "id": "v1",
                    "name": "Test",
                    "kategorien": [{"name": "K1", "gegenstaende": []}],
                }
            ]
        }
        with NamedTemporaryFile("w+", delete=True, suffix=".json") as tmp:
            tmp.write(json.dumps(payload))
            tmp.flush()
            with mock.patch("main._vorlagen_datei", return_value=Path(tmp.name)):
                vorlagen = lade_vorlagen()
        self.assertEqual(len(vorlagen), 1)
        self.assertEqual(vorlagen[0]["id"], "v1")
        self.assertEqual(vorlagen[0]["name"], "Test")

    def test_lade_vorlagen_invalid_json_returns_empty(self):
        with NamedTemporaryFile("w+", delete=True, suffix=".json") as tmp:
            tmp.write("{this is invalid json")
            tmp.flush()
            with mock.patch("main._vorlagen_datei", return_value=Path(tmp.name)):
                vorlagen = lade_vorlagen()
        self.assertEqual(vorlagen, [])

    def test_finde_vorlage(self):
        data = [{"id": "a", "name": "A"}, {"id": "b", "name": "B"}]
        self.assertEqual(finde_vorlage(data, "b")["name"], "B")
        self.assertIsNone(finde_vorlage(data, "x"))

    def test_fortschritt_berechnen_and_kat_counts(self):
        r = ReiseModel.create(
            name="Trip",
            ziel="B",
            startdatum=date(2024, 1, 1),
            enddatum=date(2024, 1, 1),
            beschreibung="",
        )
        kat = KategorieModel.create(name="K1", reise=r)
        self.assertEqual(kat.anzahl_gesamt(), 0)
        self.assertEqual(kat.anzahl_gepackt(), 0)

        GegenstandModel.create(name="A", menge=1, gepackt=False, kategorie=kat)
        GegenstandModel.create(name="B", menge=1, gepackt=True, kategorie=kat)

        self.assertEqual(kat.anzahl_gesamt(), 2)
        self.assertEqual(kat.anzahl_gepackt(), 1)
        # 1 von 2 gepackt -> 50%
        self.assertEqual(r.fortschritt_berechnen(), 50)
