import unittest
from unittest.mock import patch, mock_open
import json

# Importieren der zu testenden Funktion direkt aus der main.py
from main import lade_vorlagen


class TestMainFunktionen(unittest.TestCase):

    def test_erfolgreiches_laden(self):
        """
        Testet, ob die JSON-Datei erfolgreich geladen und der Inhalt korrekt zurückgegeben wird.
        """
        # 1. Arrange: Bereite Testdaten vor
        mock_data = {
            "vorlagen": [{"id": "test-v1", "name": "Test Vorlage", "kategorien": []}]
        }
        mock_json_string = json.dumps(mock_data)

        # Simuliere das Öffnen und Lesen der Datei.
        # Wir patchen `Path.read_text`, da dies in `lade_vorlagen` verwendet wird.
        # `mock_open` wird nicht mehr benötigt, da wir den gelesenen Text direkt zurückgeben.
        with patch("main.Path.exists", return_value=True), patch(
            "main.Path.read_text", return_value=mock_json_string
        ):

            # 2. Act: Führe die zu testende Funktion aus
            vorlagen = lade_vorlagen()

            # 3. Assert: Überprüfe das Ergebnis
            self.assertEqual(len(vorlagen), 1)
            self.assertEqual(vorlagen[0]["id"], "test-v1")
            self.assertEqual(vorlagen[0]["name"], "Test Vorlage")

    def test_fehlerbehandlung_datei_nicht_gefunden(self):
        """
        Testet das Verhalten, wenn die Datei nicht existiert.
        Die Funktion sollte eine leere Liste zurückgeben.
        """
        # 1. Arrange: Simuliere, dass `Path.exists()` False zurückgibt.
        #    Dies ist der einfachste Weg, diesen Fall in der `main.lade_vorlagen` zu testen.
        with patch("main.Path.exists", return_value=False):
            # 2. Act: Führe die Funktion aus
            vorlagen = lade_vorlagen()

            # 3. Assert: Überprüfe, ob eine leere Liste zurückgegeben wird
            self.assertEqual(vorlagen, [])

    def test_strukturpruefung(self):
        """
        Überprüft, ob die geladenen Daten die erwartete Grundstruktur haben.
        """
        # Arrange: Bereite valide Testdaten vor.
        mock_data = {
            "vorlagen": [{"id": "v1", "name": "Struktur Test", "kategorien": ["test"]}]
        }
        mock_json_string = json.dumps(mock_data)

        with patch("main.Path.exists", return_value=True), patch(
            "main.Path.read_text", return_value=mock_json_string
        ):
            # Act: Führe die Funktion aus.
            vorlagen = lade_vorlagen()

            # Assert: Überprüfe die Struktur.
            self.assertTrue(
                len(vorlagen) > 0, "Die Vorlagenliste sollte nicht leer sein."
            )
            erste_vorlage = vorlagen[0]
            self.assertIn("id", erste_vorlage)
            self.assertIn("name", erste_vorlage)
            self.assertIn("kategorien", erste_vorlage)
            self.assertIsInstance(erste_vorlage["kategorien"], list)


if __name__ == "__main__":
    unittest.main()
