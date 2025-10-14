from datetime import date
from typing import List


class Gegenstand:  # Repräsentiert einen einzelnen Gegenstand, der eingepackt werden soll.
    def __init__(self, name: str, menge: int = 1, gepackt: bool = False):
        self.name = name
        self.menge = menge
        self.gepackt = gepackt

    def als_gepackt_markieren(self):  # Markiert den Gegenstand als gepackt.
        self.gepackt = True

    def __repr__(self):
        status = "✅" if self.gepackt else "⬜"
        return f"{status} {self.name} (x{self.menge})"


class Kategorie:  # Fasst mehrere Gegenstände einer bestimmten Art zusammen (z. B. Kleidung, Technik)
    def __init__(self, name: str):
        self.name = name
        self.gegenstaende: List[Gegenstand] = []

    def gegenstand_hinzufuegen(
        self, gegenstand: Gegenstand
    ):  # Fügt der Kategorie einen neuen Gegenstand hinzu
        self.gegenstaende.append(gegenstand)

    def anzahl_gepackt(
        self,
    ) -> int:  # Zählt, wie viele Gegenstände in dieser Kategorie gepackt sind
        return sum(1 for g in self.gegenstaende if g.gepackt)

    def anzahl_gesamt(
        self,
    ) -> int:  # Zählt die Gesamtanzahl der Gegenstände in dieser Kategorie
        return len(self.gegenstaende)

    def __repr__(self):
        return f"Kategorie({self.name}, {len(self.gegenstaende)} Gegenstände)"


class Reise:  # Repräsentiert eine Reise mit verschiedenen Kategorien und Gegenständen
    def __init__(
        self, name: str, startdatum: date, enddatum: date, beschreibung: str = ""
    ):
        self.name = name
        self.startdatum = startdatum
        self.enddatum = enddatum
        self.beschreibung = beschreibung
        self.kategorien: List[Kategorie] = []

    def kategorie_hinzufuegen(
        self, kategorie: Kategorie
    ):  # Fügt der Reise eine neue Kategorie hinzu
        self.kategorien.append(kategorie)

    def fortschritt_berechnen(
        self,
    ) -> float:  # Berechnet den Packfortschritt in Prozent
        alle_gegenstaende = [g for k in self.kategorien for g in k.gegenstaende]
        if not alle_gegenstaende:
            return 0.0
        gepackt = sum(1 for g in alle_gegenstaende if g.gepackt)
        return round((gepackt / len(alle_gegenstaende)) * 100, 2)

    def __repr__(self):
        return f"Reise({self.name}, {len(self.kategorien)} Kategorien, {self.fortschritt_berechnen()}% gepackt)"
