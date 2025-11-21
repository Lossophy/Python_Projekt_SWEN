"""PackAttack GUI-Anwendung zum Erstellen und Verwalten von Packlisten."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import List, Optional

import tkinter as tk
from tkinter import messagebox, simpledialog, ttk

DATA_FILE = Path(__file__).with_name("packattack_data.json")


@dataclass
class Item:
    name: str
    quantity: int = 1
    notes: str = ""
    packed: bool = False

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: dict) -> "Item":
        quantity = data.get("quantity", 1)
        try:
            quantity_int = int(quantity)
        except (TypeError, ValueError):
            quantity_int = 1
        if quantity_int <= 0:
            quantity_int = 1
        return Item(
            name=data.get("name", "Unbenanntes Item"),
            quantity=quantity_int,
            notes=data.get("notes", ""),
            packed=bool(data.get("packed", False)),
        )


@dataclass
class Category:
    name: str
    items: List[Item] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"name": self.name, "items": [item.to_dict() for item in self.items]}

    @staticmethod
    def from_dict(data: dict) -> "Category":
        items = [Item.from_dict(entry) for entry in data.get("items", [])]
        return Category(name=data.get("name", "Unbenannte Kategorie"), items=items)


@dataclass
class Trip:
    title: str
    destination: str = ""
    start_date: str = ""
    notes: str = ""
    categories: List[Category] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "destination": self.destination,
            "start_date": self.start_date,
            "notes": self.notes,
            "categories": [category.to_dict() for category in self.categories],
        }

    @staticmethod
    def from_dict(data: dict) -> "Trip":
        categories = [Category.from_dict(entry) for entry in data.get("categories", [])]
        return Trip(
            title=data.get("title", "Unbenannte Reise"),
            destination=data.get("destination", ""),
            start_date=data.get("start_date", ""),
            notes=data.get("notes", ""),
            categories=categories,
        )

    def total_items(self) -> int:
        return sum(len(category.items) for category in self.categories)

    def packed_items(self) -> int:
        return sum(
            1 for category in self.categories for item in category.items if item.packed
        )


class PackAttackStore:
    def __init__(self, data_file: Path = DATA_FILE) -> None:
        self.data_file = data_file
        self.trips: List[Trip] = []
        self.load()

    def load(self) -> None:
        if not self.data_file.exists():
            self.trips = []
            return
        try:
            raw = self.data_file.read_text(encoding="utf-8")
        except OSError as exc:
            print(f"Warnung: Konnte Daten nicht lesen ({exc}).")
            self.trips = []
            return
        if not raw.strip():
            self.trips = []
            return
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"Warnung: Konnte JSON nicht parsen ({exc}).")
            self.trips = []
            return
        if isinstance(payload, dict):
            entries = payload.get("trips", [])
        elif isinstance(payload, list):
            entries = payload
        else:
            entries = []
        self.trips = [Trip.from_dict(entry) for entry in entries]

    def save(self) -> None:
        payload = {"trips": [trip.to_dict() for trip in self.trips]}
        try:
            self.data_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror(
                "Speicherfehler", f"Daten konnten nicht gespeichert werden: {exc}"
            )


class PackAttackGUI:
    def __init__(self, root: tk.Tk, store: PackAttackStore) -> None:
        self.root = root
        self.store = store
        self.current_trip: Optional[Trip] = None
        self.current_category: Optional[Category] = None
        self.active_view: str = "trips"
        self.trip_listbox: Optional[tk.Listbox] = None
        self.category_listbox: Optional[tk.Listbox] = None
        self.item_listbox: Optional[tk.Listbox] = None

        self.status_var = tk.StringVar(value="")

        self.setup_style()
        self.build_layout()
        self.show_trip_list()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def setup_style(self) -> None:
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("TButton", font=("Segoe UI", 10), padding=6)
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.map(
            "Accent.TButton",
            background=[("active", "#3648a5"), ("!disabled", "#3f51b5")],
            foreground=[("!disabled", "#ffffff")],
        )

    def build_layout(self) -> None:
        self.root.title("PackAttack")
        self.root.configure(bg="#111111")
        self.root.minsize(420, 760)
        self.root.geometry("420x760")

        outer = tk.Frame(self.root, bg="#111111")
        outer.pack(expand=True, fill="both")

        shell = tk.Frame(outer, bg="#222222", bd=12, relief="ridge")
        shell.place(relx=0.5, rely=0.5, anchor="center", width=380, height=720)
        shell.pack_propagate(False)

        screen = tk.Frame(shell, bg="#fafafa")
        screen.pack(expand=True, fill="both")
        screen.pack_propagate(False)

        self.header_frame = tk.Frame(screen, bg="#3f51b5", height=64)
        self.header_frame.pack(fill="x")
        self.header_frame.pack_propagate(False)

        self.back_button = ttk.Button(
            self.header_frame,
            text="<",
            width=3,
            command=self.on_back,
        )
        self.back_button.pack(side="left", padx=(12, 0), pady=12)

        self.header_title = tk.Label(
            self.header_frame,
            text="PackAttack",
            font=("Segoe UI", 16, "bold"),
            fg="#ffffff",
            bg="#3f51b5",
        )
        self.header_title.pack(side="left", padx=12)

        self.content_frame = tk.Frame(screen, bg="#fafafa")
        self.content_frame.pack(expand=True, fill="both")

        status_frame = tk.Frame(screen, bg="#fafafa")
        status_frame.pack(fill="x", pady=(0, 8))
        tk.Label(
            status_frame,
            textvariable=self.status_var,
            font=("Segoe UI", 9),
            fg="#555555",
            bg="#fafafa",
        ).pack(side="left", padx=16)

    def set_header(self, title: str, show_back: bool) -> None:
        self.header_title.config(text=title)
        if show_back:
            if not self.back_button.winfo_ismapped():
                self.back_button.pack(side="left", padx=(12, 0), pady=12)
        else:
            if self.back_button.winfo_ismapped():
                self.back_button.pack_forget()

    def reset_content(self) -> None:
        for child in self.content_frame.winfo_children():
            child.destroy()
        self.trip_listbox = None
        self.category_listbox = None
        self.item_listbox = None

    def on_back(self) -> None:
        if self.active_view == "items":
            self.show_category_view(self.current_trip)
        elif self.active_view == "categories":
            self.show_trip_list()

    def show_trip_list(self) -> None:
        self.active_view = "trips"
        self.current_trip = None
        self.current_category = None
        self.set_header("Reisen", show_back=False)
        self.status_var.set("Reisen verwalten, neue Ziele anlegen oder fortsetzen.")
        self.reset_content()

        frame = tk.Frame(self.content_frame, bg="#fafafa")
        frame.pack(expand=True, fill="both", padx=16, pady=16)

        list_container = tk.Frame(frame, bg="#fafafa")
        list_container.pack(expand=True, fill="both")

        self.trip_listbox = tk.Listbox(
            list_container,
            font=("Segoe UI", 11),
            activestyle="none",
            selectbackground="#3f51b5",
            selectforeground="#ffffff",
            bg="#ffffff",
            bd=0,
            highlightthickness=0,
        )
        self.trip_listbox.pack(side="left", expand=True, fill="both")

        scrollbar = ttk.Scrollbar(
            list_container, orient="vertical", command=self.trip_listbox.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.trip_listbox.config(yscrollcommand=scrollbar.set)

        button_frame = tk.Frame(frame, bg="#fafafa")
        button_frame.pack(fill="x", pady=(18, 0))

        ttk.Button(
            button_frame,
            text="Reise anlegen",
            style="Accent.TButton",
            command=self.add_trip,
        ).pack(fill="x", pady=4)
        ttk.Button(button_frame, text="Reise bearbeiten", command=self.edit_trip).pack(
            fill="x", pady=4
        )
        ttk.Button(button_frame, text="Reise loeschen", command=self.delete_trip).pack(
            fill="x", pady=4
        )
        ttk.Button(button_frame, text="Reise oeffnen", command=self.open_trip).pack(
            fill="x", pady=4
        )

        self.refresh_trip_list()

    def refresh_trip_list(self) -> None:
        if not self.trip_listbox or not self.trip_listbox.winfo_exists():
            return
        self.trip_listbox.delete(0, tk.END)
        if not self.store.trips:
            self.trip_listbox.insert(tk.END, "Noch keine Reisen gespeichert.")
            self.trip_listbox.config(state="disabled")
            return
        self.trip_listbox.config(state="normal")
        for trip in self.store.trips:
            total = trip.total_items()
            packed = trip.packed_items()
            status = f"{packed}/{total} gepackt" if total else "Keine Items"
            destination = f" | {trip.destination}" if trip.destination else ""
            self.trip_listbox.insert(tk.END, f"{trip.title}{destination} ({status})")

    def get_selected_trip(self) -> Optional[Trip]:
        if not self.trip_listbox or not self.store.trips:
            return None
        selection = self.trip_listbox.curselection()
        if not selection:
            messagebox.showinfo(
                "Auswahl", "Bitte zuerst eine Reise auswaehlen.", parent=self.root
            )
            return None
        index = selection[0]
        return self.store.trips[index]

    def add_trip(self) -> None:
        title = simpledialog.askstring(
            "Neue Reise", "Wie lautet der Name der Reise?", parent=self.root
        )
        if title is None:
            return
        title = title.strip()
        if not title:
            messagebox.showwarning(
                "Eingabe fehlt", "Der Name darf nicht leer sein.", parent=self.root
            )
            return
        destination = (
            simpledialog.askstring(
                "Reiseziel", "Reiseziel (optional):", parent=self.root
            )
            or ""
        )
        start_date = (
            simpledialog.askstring(
                "Startdatum", "Startdatum (optional):", parent=self.root
            )
            or ""
        )
        notes = (
            simpledialog.askstring("Notizen", "Notizen (optional):", parent=self.root)
            or ""
        )
        trip = Trip(
            title=title,
            destination=destination.strip(),
            start_date=start_date.strip(),
            notes=notes.strip(),
        )
        self.store.trips.append(trip)
        self.store.save()
        self.refresh_trip_list()
        self.status_var.set(f"Reise '{trip.title}' wurde angelegt.")

    def edit_trip(self) -> None:
        trip = self.get_selected_trip()
        if not trip:
            return
        title = simpledialog.askstring(
            "Reise bearbeiten",
            "Neuer Name der Reise:",
            initialvalue=trip.title,
            parent=self.root,
        )
        if title is None:
            return
        title = title.strip()
        if title:
            trip.title = title
        destination = simpledialog.askstring(
            "Reiseziel",
            "Reiseziel (leer fuer keine Angabe):",
            initialvalue=trip.destination,
            parent=self.root,
        )
        if destination is not None:
            trip.destination = destination.strip()
        start_date = simpledialog.askstring(
            "Startdatum",
            "Startdatum (leer fuer keine Angabe):",
            initialvalue=trip.start_date,
            parent=self.root,
        )
        if start_date is not None:
            trip.start_date = start_date.strip()
        notes = simpledialog.askstring(
            "Notizen",
            "Notizen (leer fuer keine Angabe):",
            initialvalue=trip.notes,
            parent=self.root,
        )
        if notes is not None:
            trip.notes = notes.strip()
        self.store.save()
        self.refresh_trip_list()
        self.status_var.set(f"Reise '{trip.title}' wurde aktualisiert.")

    def delete_trip(self) -> None:
        trip = self.get_selected_trip()
        if not trip:
            return
        if not messagebox.askyesno(
            "Reise loeschen",
            f"Soll die Reise '{trip.title}' inklusive Kategorien und Items wirklich geloescht werden?",
            parent=self.root,
        ):
            return
        self.store.trips.remove(trip)
        self.store.save()
        self.refresh_trip_list()
        self.status_var.set(f"Reise '{trip.title}' wurde geloescht.")

    def open_trip(self) -> None:
        trip = self.get_selected_trip()
        if not trip:
            return
        self.show_category_view(trip)

    def show_category_view(self, trip: Trip) -> None:
        self.active_view = "categories"
        self.current_trip = trip
        self.current_category = None
        header = trip.title if len(trip.title) <= 22 else trip.title[:22] + "..."
        self.set_header(header, show_back=True)
        subtitle = trip.destination or "Ohne Reiseziel"
        progress = trip.packed_items()
        total = trip.total_items()
        status = f"{progress}/{total} gepackt" if total else "Noch keine Items"
        self.status_var.set(f"{subtitle} | {status}")
        self.reset_content()

        frame = tk.Frame(self.content_frame, bg="#fafafa")
        frame.pack(expand=True, fill="both", padx=16, pady=16)

        info_frame = tk.Frame(frame, bg="#e8eaf6", bd=0)
        info_frame.pack(fill="x", pady=(0, 12))
        info_frame.pack_propagate(False)
        info_label = tk.Label(
            info_frame,
            text=self.build_trip_info(trip),
            justify="left",
            anchor="w",
            fg="#303f9f",
            bg="#e8eaf6",
            font=("Segoe UI", 10),
            wraplength=320,
        )
        info_label.pack(fill="both", padx=12, pady=8)

        list_container = tk.Frame(frame, bg="#fafafa")
        list_container.pack(expand=True, fill="both")

        self.category_listbox = tk.Listbox(
            list_container,
            font=("Segoe UI", 11),
            activestyle="none",
            selectbackground="#3f51b5",
            selectforeground="#ffffff",
            bg="#ffffff",
            bd=0,
            highlightthickness=0,
        )
        self.category_listbox.pack(side="left", expand=True, fill="both")

        scrollbar = ttk.Scrollbar(
            list_container, orient="vertical", command=self.category_listbox.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.category_listbox.config(yscrollcommand=scrollbar.set)

        button_frame = tk.Frame(frame, bg="#fafafa")
        button_frame.pack(fill="x", pady=(18, 0))

        ttk.Button(
            button_frame,
            text="Kategorie anlegen",
            style="Accent.TButton",
            command=self.add_category,
        ).pack(fill="x", pady=4)
        ttk.Button(
            button_frame, text="Kategorie umbenennen", command=self.rename_category
        ).pack(fill="x", pady=4)
        ttk.Button(
            button_frame, text="Kategorie loeschen", command=self.delete_category
        ).pack(fill="x", pady=4)
        ttk.Button(button_frame, text="Items ansehen", command=self.open_category).pack(
            fill="x", pady=4
        )

        self.refresh_category_list()

    def build_trip_info(self, trip: Trip) -> str:
        destination = trip.destination or "Ziel offen"
        start_date = trip.start_date or "kein Datum"
        notes = trip.notes or "keine Notizen"
        return f"Ziel: {destination}\nStart: {start_date}\nNotizen: {notes}"

    def refresh_category_list(self) -> None:
        if not self.category_listbox or not self.category_listbox.winfo_exists():
            return
        self.category_listbox.delete(0, tk.END)
        trip = self.current_trip
        if not trip or not trip.categories:
            self.category_listbox.insert(tk.END, "Noch keine Kategorien hinterlegt.")
            self.category_listbox.config(state="disabled")
            return
        self.category_listbox.config(state="normal")
        for category in trip.categories:
            total = len(category.items)
            packed = sum(1 for item in category.items if item.packed)
            status = f"{packed}/{total} gepackt" if total else "Leer"
            self.category_listbox.insert(tk.END, f"{category.name} ({status})")

    def get_selected_category(self) -> Optional[Category]:
        if not self.category_listbox or not self.current_trip:
            return None
        selection = self.category_listbox.curselection()
        if not selection:
            messagebox.showinfo(
                "Auswahl", "Bitte zuerst eine Kategorie waehlen.", parent=self.root
            )
            return None
        index = selection[0]
        return self.current_trip.categories[index]

    def add_category(self) -> None:
        if not self.current_trip:
            return
        name = simpledialog.askstring(
            "Kategorie", "Name der Kategorie:", parent=self.root
        )
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showwarning(
                "Eingabe fehlt", "Der Name darf nicht leer sein.", parent=self.root
            )
            return
        self.current_trip.categories.append(Category(name=name))
        self.store.save()
        self.refresh_category_list()
        self.status_var.set(f"Kategorie '{name}' wurde angelegt.")

    def rename_category(self) -> None:
        category = self.get_selected_category()
        if not category:
            return
        name = simpledialog.askstring(
            "Kategorie umbenennen",
            "Neuer Name der Kategorie:",
            initialvalue=category.name,
            parent=self.root,
        )
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showwarning(
                "Eingabe fehlt", "Der Name darf nicht leer sein.", parent=self.root
            )
            return
        category.name = name
        self.store.save()
        self.refresh_category_list()
        self.status_var.set(f"Kategorie wurde in '{name}' umbenannt.")

    def delete_category(self) -> None:
        category = self.get_selected_category()
        if not category or not self.current_trip:
            return
        if not messagebox.askyesno(
            "Kategorie loeschen",
            f"Soll die Kategorie '{category.name}' inklusive Items geloescht werden?",
            parent=self.root,
        ):
            return
        self.current_trip.categories.remove(category)
        self.store.save()
        self.refresh_category_list()
        self.status_var.set(f"Kategorie '{category.name}' wurde geloescht.")

    def open_category(self) -> None:
        category = self.get_selected_category()
        if not category:
            return
        self.show_items_view(category)

    def show_items_view(self, category: Category) -> None:
        self.active_view = "items"
        self.current_category = category
        header = (
            category.name if len(category.name) <= 22 else category.name[:22] + "..."
        )
        self.set_header(header, show_back=True)
        packed = sum(1 for item in category.items if item.packed)
        total = len(category.items)
        status = f"{packed}/{total} gepackt" if total else "Noch keine Items"
        self.status_var.set(status)
        self.reset_content()

        frame = tk.Frame(self.content_frame, bg="#fafafa")
        frame.pack(expand=True, fill="both", padx=16, pady=16)

        list_container = tk.Frame(frame, bg="#fafafa")
        list_container.pack(expand=True, fill="both")

        self.item_listbox = tk.Listbox(
            list_container,
            font=("Segoe UI", 11),
            activestyle="none",
            selectbackground="#3f51b5",
            selectforeground="#ffffff",
            bg="#ffffff",
            bd=0,
            highlightthickness=0,
        )
        self.item_listbox.pack(side="left", expand=True, fill="both")

        scrollbar = ttk.Scrollbar(
            list_container, orient="vertical", command=self.item_listbox.yview
        )
        scrollbar.pack(side="right", fill="y")
        self.item_listbox.config(yscrollcommand=scrollbar.set)

        button_frame = tk.Frame(frame, bg="#fafafa")
        button_frame.pack(fill="x", pady=(18, 0))

        ttk.Button(
            button_frame,
            text="Item hinzufuegen",
            style="Accent.TButton",
            command=self.add_item,
        ).pack(fill="x", pady=4)
        ttk.Button(
            button_frame, text="Status umschalten", command=self.toggle_item
        ).pack(fill="x", pady=4)
        ttk.Button(button_frame, text="Item bearbeiten", command=self.edit_item).pack(
            fill="x", pady=4
        )
        ttk.Button(button_frame, text="Item loeschen", command=self.delete_item).pack(
            fill="x", pady=4
        )

        self.refresh_item_list()

    def refresh_item_list(self) -> None:
        if not self.item_listbox or not self.item_listbox.winfo_exists():
            return
        self.item_listbox.delete(0, tk.END)
        category = self.current_category
        if not category or not category.items:
            self.item_listbox.insert(tk.END, "Noch keine Items angelegt.")
            self.item_listbox.config(state="disabled")
            return
        self.item_listbox.config(state="normal")
        for item in category.items:
            checkbox = "[x]" if item.packed else "[ ]"
            qty = f" x{item.quantity}" if item.quantity != 1 else ""
            notes = f" - {item.notes}" if item.notes else ""
            self.item_listbox.insert(tk.END, f"{checkbox} {item.name}{qty}{notes}")

    def get_selected_item(self) -> Optional[Item]:
        if not self.item_listbox or not self.current_category:
            return None
        selection = self.item_listbox.curselection()
        if not selection:
            messagebox.showinfo(
                "Auswahl", "Bitte zuerst ein Item waehlen.", parent=self.root
            )
            return None
        index = selection[0]
        return self.current_category.items[index]

    def add_item(self) -> None:
        if not self.current_category:
            return
        name = simpledialog.askstring("Item", "Name des Items:", parent=self.root)
        if name is None:
            return
        name = name.strip()
        if not name:
            messagebox.showwarning(
                "Eingabe fehlt", "Der Name darf nicht leer sein.", parent=self.root
            )
            return
        quantity = simpledialog.askinteger(
            "Menge",
            "Wie viele davon brauchst du?",
            parent=self.root,
            minvalue=1,
            initialvalue=1,
        )
        if quantity is None:
            return
        notes = (
            simpledialog.askstring("Notizen", "Notizen (optional):", parent=self.root)
            or ""
        )
        self.current_category.items.append(
            Item(name=name, quantity=quantity, notes=notes.strip())
        )
        self.store.save()
        self.refresh_item_list()
        packed = sum(1 for entry in self.current_category.items if entry.packed)
        total = len(self.current_category.items)
        self.status_var.set(
            f"Item '{name}' wurde hinzugefuegt ({packed}/{total} gepackt)."
        )

    def toggle_item(self) -> None:
        item = self.get_selected_item()
        if not item:
            return
        item.packed = not item.packed
        self.store.save()
        self.refresh_item_list()
        packed = sum(1 for entry in self.current_category.items if entry.packed)
        total = len(self.current_category.items)
        self.status_var.set(f"{packed}/{total} gepackt")

    def edit_item(self) -> None:
        item = self.get_selected_item()
        if not item:
            return
        name = simpledialog.askstring(
            "Item bearbeiten", "Neuer Name:", initialvalue=item.name, parent=self.root
        )
        if name is None:
            return
        name = name.strip()
        if name:
            item.name = name
        quantity = simpledialog.askinteger(
            "Menge",
            "Neue Menge:",
            parent=self.root,
            minvalue=1,
            initialvalue=item.quantity,
        )
        if quantity is not None:
            item.quantity = max(1, quantity)
        notes = simpledialog.askstring(
            "Notizen",
            "Neue Notizen (leer fuer keine):",
            initialvalue=item.notes,
            parent=self.root,
        )
        if notes is not None:
            item.notes = notes.strip()
        self.store.save()
        self.refresh_item_list()
        self.status_var.set(f"Item '{item.name}' wurde aktualisiert.")

    def delete_item(self) -> None:
        item = self.get_selected_item()
        if not item or not self.current_category:
            return
        if not messagebox.askyesno(
            "Item loeschen",
            f"Soll '{item.name}' wirklich geloescht werden?",
            parent=self.root,
        ):
            return
        self.current_category.items.remove(item)
        self.store.save()
        self.refresh_item_list()
        packed = sum(1 for entry in self.current_category.items if entry.packed)
        total = len(self.current_category.items)
        self.status_var.set(
            f"{packed}/{total} gepackt" if total else "Noch keine Items"
        )

    def on_close(self) -> None:
        self.store.save()
        self.root.destroy()


def main() -> None:
    store = PackAttackStore()
    root = tk.Tk()
    PackAttackGUI(root, store)
    root.mainloop()


if __name__ == "__main__":
    main()
