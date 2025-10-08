!! Change this document for your own project by removing the placeholder text, adding your own text, adding helpful sections etc. etc. !!

# PackAttack

Wir sind eine bunte Truppe, die das Problem kennt: Koffer gepackt, aber irgendetwas fehlt immer. Mit unserer Reise- und Packlisten-App wollen wir genau das vermeiden. Gemeinsam programmieren wir eine App, die Ordnung ins Pack-Chaos bringt. Vielleicht können wir sogar verhindern, dass Socken und Ladegeräte zuhause bleiben.


## Get started

Explain what the user has to type to get started with your solution. Which one
is the main Python file? In the simplest case, this could look something like
this:

``
    python main.py
``

In other cases the user might first have to install some project dependencies
first has to run something like this (a sample requirements.txt file is also
included in the project template):

``
    pip install -r requirements.txt
``

## Anforderungen an die Webapplikation

### Funktionale Anforderungen
| **Nr.** | **Anforderung**          | **Beschreibung**                                                                                |
| ------- | ------------------------ | ----------------------------------------------------------------------------------------------- |
| **F1**  | Reise anlegen            | Benutzer*innen können eine neue Reise mit Name, Reisedatum und Zielort erfassen.                |
| **F2**  | Kategorien erstellen     | Es sollen beliebige Kategorien pro Reise definierbar sein (z. B. Kleidung, Technik, Dokumente). |
| **F3**  | Gegenstände hinzufügen   | Zu jeder Kategorie können beliebig viele Gegenstände erfasst werden.                            |
| **F4**  | Gegenstände abhaken      | Gegenstände können als „gepackt“ markiert werden.                                               |
| **F5**  | Fortschrittsanzeige      | Der Fortschritt (z. B. 12/20 Gegenstände gepackt) wird pro Reise angezeigt.                     |
| **F6**  | Listen speichern & laden | Alle Daten werden gespeichert, sodass sie bei erneutem Öffnen wieder verfügbar sind.            |
| **F7**  | Listen löschen           | Benutzer*innen können komplette Packlisten oder einzelne Einträge löschen.                      |
| **F8** | Vorlagen verwenden       | Es können Standard-Listen als Vorlage genutzt werden (z. B. „Strandurlaub“, „Städtereise“).     |

### Nicht-funktionale Anforderungen
| **Nr.** | **Anforderung**        | **Beschreibung**                                                                                  |
| ------- | ---------------------- | ------------------------------------------------------------------------------------------------- |
| **NF1** | Benutzerfreundlichkeit | Die Oberfläche soll intuitiv, klar strukturiert und auch für Erstnutzer*innen verständlich sein.  |
| **NF2** | Wartbarkeit            | Der Quellcode soll nach definierten Code Conventions aufgebaut sein und klar dokumentiert werden. |
| **NF3** | Erweiterbarkeit        | Neue Funktionen (z. B. Versand der Liste) sollen leicht ergänzt werden können.    |
| **NF4** | Designfreiheit         | Das Layout ist frei gestaltbar, muss jedoch klar und funktional sein.                             |


## Understanding the sources

Explain any high level concepts that you are using in your software. What were
your ideas for creating the whole software? What might not be apparent from the
sources alone? You can also add diagrams, photos of whiteboards or flipcharts
or even crudly drawing napkin sketches of the core concepts of your software
when they are readable and helpful for understanding.
