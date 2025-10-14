from datetime import date
from backend.modelle import Reise, Kategorie, Gegenstand


def beispielreisen_laden() -> (
    list[Reise]
):  # Erstellt eine Liste mit Beispielreisen, die beim App-Start angezeigt werden können."""
    reisen = []

    # Beispiel 1 – Städtereise
    stadt = Reise(
        "Städtereise", date(2025, 5, 10), date(2025, 5, 14), "Kurztrip in die Stadt"
    )
    kleidung = Kategorie("Kleidung")
    kleidung.gegenstand_hinzufuegen(Gegenstand("Hose", 2))
    kleidung.gegenstand_hinzufuegen(Gegenstand("T-Shirt", 3))
    technik = Kategorie("Technik")
    technik.gegenstand_hinzufuegen(Gegenstand("Handyladegerät"))
    technik.gegenstand_hinzufuegen(Gegenstand("Kamera", 1, gepackt=True))
    stadt.kategorie_hinzufuegen(kleidung)
    stadt.kategorie_hinzufuegen(technik)
    reisen.append(stadt)

    # Beispiel 2 – Wanderurlaub
    wandern = Reise(
        "Wanderferien Alpen",
        date(2025, 8, 1),
        date(2025, 8, 10),
        "Outdoor-Abenteuer in der Schweiz",
    )
    ausruestung = Kategorie("Ausrüstung")
    ausruestung.gegenstand_hinzufuegen(Gegenstand("Wanderschuhe"))
    ausruestung.gegenstand_hinzufuegen(Gegenstand("Rucksack"))
    wandern.kategorie_hinzufuegen(ausruestung)
    reisen.append(wandern)

    return reisen
