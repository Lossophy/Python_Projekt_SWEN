from datetime import date
from Backend.backend import Reise, Kategorie, Gegenstand


def beispielreisen_laden() -> (
    list[Reise]
):  # Erstellt eine Liste mit Beispielreisen, die beim App-Start angezeigt werden können
    reisen = []

    # Beispiel 1 – Städtereise
    stadt = Reise("Städtereise", date(2026, 5, 10), date(2026, 5, 14), "Kurztrip")
    kleidung = Kategorie("Kleidung")
    kleidung.gegenstand_hinzufuegen(Gegenstand("Hose", 2))
    kleidung.gegenstand_hinzufuegen(Gegenstand("T-Shirt", 3))
    kleidung.gegenstand_hinzufuegen(Gegenstand("Leichte Jacke", 1))
    kleidung.gegenstand_hinzufuegen(Gegenstand("Unterwäsche", 5))

    technik = Kategorie("Technik")
    technik.gegenstand_hinzufuegen(Gegenstand("Handyladegerät"))
    technik.gegenstand_hinzufuegen(Gegenstand("Kamera", 1, gepackt=True))

    accessoire = Kategorie("Accessoire")
    accessoire.gegenstand_hinzufuegen(Gegenstand("Sonnenbrille", 1))

    sonstiges = Kategorie("Sonstiges")
    sonstiges.gegenstand_hinzufuegen(Gegenstand("Bahnticket", 1))
    sonstiges.gegenstand_hinzufuegen(Gegenstand("Pass oder ID", 1))
    sonstiges.gegenstand_hinzufuegen(Gegenstand("Geld ca. 500€", 1))
    sonstiges.gegenstand_hinzufuegen(Gegenstand("Verpflegung für Unterwegs", 1))

    stadt.kategorie_hinzufuegen(kleidung)
    stadt.kategorie_hinzufuegen(technik)
    stadt.kategorie_hinzufuegen(accessoire)
    stadt.kategorie_hinzufuegen(sonstiges)
    reisen.append(stadt)

    # Beispiel 2 – Wanderurlaub
    wandern = Reise(
        "Wanderferien Alpen",
        date(2026, 8, 1),
        date(2026, 8, 10),
        "Outdoor-Abenteuer in der Schweiz",
    )
    ausruestung = Kategorie("Ausrüstung")
    ausruestung.gegenstand_hinzufuegen(Gegenstand("Wanderschuhe", 1))
    ausruestung.gegenstand_hinzufuegen(Gegenstand("Rucksack", 1))
    ausruestung.gegenstand_hinzufuegen(Gegenstand("Schlafsack", 1))
    ausruestung.gegenstand_hinzufuegen(Gegenstand("Nothilfeset", 1))
    ausruestung.gegenstand_hinzufuegen(Gegenstand("Blasenpflaster", 1))

    accessoire = Kategorie("Accessoire")
    accessoire.gegenstand_hinzufuegen(Gegenstand("Sonnenbrille", 1))
    accessoire.gegenstand_hinzufuegen(Gegenstand("Sonnencreme", 1))
    accessoire.gegenstand_hinzufuegen(Gegenstand("Sonnenhut", 1))

    kleidung = Kategorie("Kleidung")
    kleidung.gegenstand_hinzufuegen(Gegenstand("T-Shirt", 4))
    kleidung.gegenstand_hinzufuegen(Gegenstand("Wanderhose", 1))
    kleidung.gegenstand_hinzufuegen(Gegenstand("Unterwäsche", 4))
    kleidung.gegenstand_hinzufuegen(Gegenstand("Regenhose", 1))
    kleidung.gegenstand_hinzufuegen(Gegenstand("Regenjacke", 1))

    technik = Kategorie("Technik")
    technik.gegenstand_hinzufuegen(Gegenstand("Kleines Solarpanel", 1))
    technik.gegenstand_hinzufuegen(Gegenstand("Ladekabel", 1))

    wandern.kategorie_hinzufuegen(ausruestung)
    wandern.kategorie_hinzufuegen(accessoire)
    wandern.kategorie_hinzufuegen(kleidung)
    wandern.kategorie_hinzufuegen(technik)
    reisen.append(wandern)

    return reisen
