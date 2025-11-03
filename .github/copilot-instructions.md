## Purpose

Short, practical instructions for AI coding agents working on this repository.
Focus: how the app is structured, run/debug workflows, important conventions, and where to make safe changes.

## Big-picture architecture

- Single Python service implemented in `main.py`. It exposes two UI layers:
  - Flask-based server rendering templates from `templates/` (classic web UI, port 5000 when used).
  - NiceGUI-based SPA-like UI embedded in `main.py` (runs on port 8080 by default when `USE_NICEGUI = True`).
- Data persistence uses a local SQLite DB `app.db` via Peewee ORM. Models live in `main.py`:
  - `ReiseModel` (trips), `KategorieModel` (categories), `GegenstandModel` (items).
- Lightweight file-based templates for seeding: `vorlagen.json` (list of packing templates).

## Key files & directories

- `main.py` — single entrypoint. Most logic lives here (routes, NiceGUI pages, model definitions).
- `templates/` — Flask Jinja templates: `index.html`, `reise_detail.html`, `reise_form.html`, etc.
- `vorlagen.json` — template JSON consumed by `lade_vorlagen()` and used when creating new trips.
- `requirements.txt` — Python dependencies (install before running).
- `Backend/` — contains `backend.py` and `daten.py` (project-specific backend helpers; inspect before editing).

## How to run (developer workflow)

1. Create a virtualenv and install deps:

   pip install -r requirements.txt

2. Run the app (two modes):
   - NiceGUI (recommended for development): open `main.py`, ensure `USE_NICEGUI = True` and run `python main.py`. NiceGUI serves at http://127.0.0.1:8080/.
   - Flask templates: set `USE_NICEGUI = False` in `main.py` and run `python main.py` (Flask debug server at http://127.0.0.1:5000/).

Notes:
- The app creates DB tables automatically at startup via `db.create_tables([...])` in `main.py`.
- DB file is `app.db` in the repository root. To reset local data, stop the app and remove `app.db`.

## Important conventions & patterns

- German identifiers: function/variable names and UI text are primarily German (e.g. `reise`, `kategorie`, `gegenstand`); keep naming consistent when adding code.
- Dual UI strategy: keep Flask routes and NiceGUI pages consistent. NiceGUI pages are implemented inline in `main.py` using `@ui.page(...)` and call Peewee models directly.
- DB connection handling:
  - Flask: `_db_connect()` and `_db_close()` are registered with `@app.before_request`/`@app.teardown_request`.
  - NiceGUI: helper functions `_ui_db_open()` / `_ui_db_close()` are called at page start/end.
  Always follow existing open/close patterns to avoid locked DB connections.
- Template seeding: `vorlagen.json` structure expects a top-level `"vorlagen"` list; each template has `id`, `name`, `kategorien` (each with `gegenstaende` containing `name` and optional `menge`). Use `lade_vorlagen()` to read safely.

## Integration points & external dependencies

- NiceGUI (UI) and Flask (templating) both run inside this process — switching modes is controlled by `USE_NICEGUI`.
- Peewee ORM with SQLite (file `app.db`). There is no migration tool checked into the repo; if schema changes are needed, either add lightweight migration code or drop `app.db` and let `create_tables` recreate the schema (data will be lost).

## Where to put changes

- Add new HTTP endpoints with `@app.get/post(...)` near existing Flask handlers in `main.py`.
- Add new NiceGUI pages or components using `@ui.page(...)` in `main.py`. Keep DB open/close pairing (`_ui_db_open()` / `_ui_db_close()`).
- For template changes, edit the files in `templates/` and preserve the Flask context variables used in `main.py` (e.g., `reise`, `kategorien`).

## Examples / quick references

- Create a trip programmatically (used in UI):

  ReiseModel.create(name="Name", startdatum=date.fromisoformat("2025-01-01"), enddatum=date.fromisoformat("2025-01-05"), beschreibung="...")

- Read `vorlagen.json` safely using: `vorlagen = lade_vorlagen(); v = finde_vorlage(vorlagen, chosen_id)`

## Tests / CI

- No test suite is present. When adding behaviour, include small unit tests and a simple script that exercises the run-mode (NiceGUI vs. Flask). Add `pytest` to `requirements.txt` if you add tests.

## Small gotchas discovered while reading the repo

- Changing the Peewee model definitions requires manual DB handling (no migrations present). Prefer additive nullable columns, or document migration steps.
- UI logic is split: keep behavior duplicated between Flask and NiceGUI in sync where both exist (e.g., creating trips, templates application).

## If you need more info

- I can update this file with code examples, search `Backend/` for additional helper behaviour, or add a short run/debug checklist for Windows PowerShell (current dev shell). Tell me what you'd like clarified.
