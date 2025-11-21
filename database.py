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


# Datenbank-Verbindung definieren (Foreign Keys aktivieren)
db = SqliteDatabase("app.db", pragmas={"foreign_keys": 1})


# Basis-Klasse für alle Modelle, damit sie dieselbe DB nutzen
class BaseModel(Model):
    class Meta:
        database = db


# Repräsentiert eine Reise mit Start/Ziel und Datum
class ReiseModel(BaseModel):
    class Meta:
        table_name = "reisen"

    id = AutoField()
    name = CharField(max_length=200)
    ziel = CharField(max_length=200)
    startdatum = DateField()
    enddatum = DateField()
    beschreibung = TextField(default="")

    # Berechnet, wie viel Prozent der Items gepackt sind
    def fortschritt_berechnen(self) -> float:
        total = sum(len(k.gegenstaende) for k in self.kategorien)
        if total == 0:
            return 0.0
        gepackt = sum(
            sum(1 for g in k.gegenstaende if g.gepackt) for k in self.kategorien
        )
        return round(gepackt / total * 100.0, 2)


# Eine Kategorie (z.B. "Kleidung") gehört zu einer Reise
class KategorieModel(BaseModel):
    class Meta:
        table_name = "kategorien"

    id = AutoField()
    name = CharField(max_length=200)
    reise = ForeignKeyField(ReiseModel, backref="kategorien", on_delete="CASCADE")

    # Gibt zurück, wie viele Items in dieser Kategorie erledigt sind
    def anzahl_gepackt(self) -> int:
        return sum(1 for g in self.gegenstaende if g.gepackt)

    # Gibt die Gesamtanzahl der Items in der Kategorie zurück
    def anzahl_gesamt(self) -> int:
        return len(self.gegenstaende)


# Ein einzelnes Item (z.B. "Socken") in einer Kategorie
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
