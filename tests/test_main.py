import sys
import importlib.util
import unittest
from pathlib import Path
from datetime import date
from peewee import SqliteDatabase

# Skip cleanly if NiceGUI is not available in the environment.
NICEGUI_AVAILABLE = importlib.util.find_spec("nicegui") is not None

# Ensure project root is on the import path for test runs.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import db, ReiseModel, KategorieModel, GegenstandModel
from main import (
    _berechne_menge,
    _reisedauer_tage,
    export_reise_to_dict,
    import_reise_from_dict,
)


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
