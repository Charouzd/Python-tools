import tkinter as tk
from tkinter import ttk, messagebox
import requests
import datetime
import os
import threading
import re

class StickyNote(tk.Toplevel):
    """
    Třída pro plovoucí okno s poznámkou (pouze pro čtení).
    """
    def __init__(self, master, text_content):
        super().__init__(master)
        self.title("Poznámka z minula")
        self.geometry("350x300")
        self.configure(bg="#ffeb3b")
        
        # Tlačítko zavřít (zde ho dáme dolů, aby bylo vždy vidět)
        btn_close = tk.Button(self, text="Přečteno / Zavřít", command=self.destroy, bg="#fdd835", relief="flat")
        btn_close.pack(side="bottom", fill="x", pady=5, padx=5)

        # Scrollovatelný textový widget (zbytek místa)
        self.text_area = tk.Text(self, bg="#ffeb3b", fg="black", 
                                 font=("Arial", 11), relief="flat", wrap="word", padx=10, pady=10)
        self.text_area.pack(expand=True, fill="both", side="top")
        
        # Konfigurace stylů
        self.text_area.tag_config("heading", font=("Arial", 14, "bold"), spacing3=5)
        self.text_area.tag_config("bold", font=("Arial", 11, "bold"))
        self.text_area.tag_config("italic", font=("Arial", 11, "italic"))
        self.text_area.tag_config("list", lmargin1=10, lmargin2=20)
        
        self.text_area.insert("1.0", text_content)
        self.parse_markdown()
        self.text_area.configure(state="disabled")

    def parse_markdown(self):
        count_lines = int(self.text_area.index('end-1c').split('.')[0])
        for i in range(1, count_lines + 1):
            line_text = self.text_area.get(f"{i}.0", f"{i}.end")
            if line_text.startswith("#"):
                self.text_area.tag_add("heading", f"{i}.0", f"{i}.end")
            if line_text.strip().startswith("- ") or line_text.strip().startswith("* "):
                self.text_area.tag_add("list", f"{i}.0", f"{i}.end")

        content = self.text_area.get("1.0", "end")
        for match in re.finditer(r'\*\*(.*?)\*\*', content):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            self.text_area.tag_add("bold", start, end)

        for match in re.finditer(r'_(.*?)_', content):
            start = f"1.0 + {match.start()} chars"
            end = f"1.0 + {match.end()} chars"
            self.text_area.tag_add("italic", start, end)


class NoteEditor(tk.Toplevel):
    """
    Okno pro psaní strukturované poznámky.
    """
    def __init__(self, master, on_save_callback):
        super().__init__(master)
        self.title("Nová poznámka")
        self.geometry("400x450")
        self.on_save_callback = on_save_callback

        btn_frame = ttk.Frame(self, padding=5)
        btn_frame.pack(side="bottom", fill="x")
        
        btn_save = ttk.Button(btn_frame, text="ULOŽIT POZNÁMKU", command=self.save_note)
        btn_save.pack(fill="x", ipady=5) # ipady zvětší tlačítko na výšku

        # --- Toolbar nahoře ---
        toolbar = ttk.Frame(self)
        toolbar.pack(side="top", fill="x", padx=5, pady=2)
        
        ttk.Button(toolbar, text="H1", width=3, command=lambda: self.insert_formatting("# ")).pack(side="left", padx=1)
        ttk.Button(toolbar, text="B", width=3, command=lambda: self.wrap_selection("**", "**")).pack(side="left", padx=1)
        ttk.Button(toolbar, text="I", width=3, command=lambda: self.wrap_selection("_", "_")).pack(side="left", padx=1)
        ttk.Button(toolbar, text="Seznam", command=lambda: self.insert_formatting("\n- ")).pack(side="left", padx=1)
        ttk.Button(toolbar, text="Odkaz", command=lambda: self.insert_formatting("[Odkaz](url)")).pack(side="left", padx=1)

        # --- Textová oblast ---
        self.text_input = tk.Text(self, font=("Arial", 11), wrap="word")
        self.text_input.pack(expand=True, fill="both", padx=5, pady=5)
        self.text_input.focus_set()

    def insert_formatting(self, symbol):
        self.text_input.insert(tk.INSERT, symbol)
        self.text_input.focus_set()

    def wrap_selection(self, prefix, suffix):
        try:
            sel_start = self.text_input.index("sel.first")
            sel_end = self.text_input.index("sel.last")
            selected_text = self.text_input.get(sel_start, sel_end)
            self.text_input.delete(sel_start, sel_end)
            self.text_input.insert(sel_start, f"{prefix}{selected_text}{suffix}")
        except tk.TclError:
            self.text_input.insert(tk.INSERT, f"{prefix}{suffix}")

    def save_note(self):
        content = self.text_input.get("1.0", "end-1c")
        if content.strip():
            self.on_save_callback(content)
            self.destroy()
        else:
            messagebox.showwarning("Prázdné", "Poznámka je prázdná.")


class WorkDayApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Pracovní Asistent")
        self.root.geometry("400x520") # Mírně zvětšeno pro další tlačítko
        
        self.countdown_time = datetime.timedelta(hours=7)
        self.countdown_running = False
        self.note_file = "poznamka.txt"

        self.create_widgets()
        self.update_clock()
        threading.Thread(target=self.fetch_svatek_api, daemon=True).start()
        self.check_existing_note()

    def create_widgets(self):
        style = ttk.Style()
        style.configure("TButton", font=("Helvetica", 10), padding=5)
        style.configure("TLabel", font=("Helvetica", 12))

        # Datum a Čas
        frame_top = ttk.Frame(self.root, padding=10)
        frame_top.pack(fill="x")
        
        self.date_label = ttk.Label(frame_top, text="Načítám datum...", font=("Helvetica", 14, "bold"))
        self.date_label.pack()
        self.day_in_week_label = ttk.Label(frame_top, text="", font=("Helvetica", 12))
        self.day_in_week_label.pack()
        self.time_label = ttk.Label(frame_top, text="Načítám čas...", font=("Helvetica", 20))
        self.time_label.pack(pady=5)

        # Svátek
        frame_api = ttk.LabelFrame(self.root, text="Dnes má svátek", padding=10)
        frame_api.pack(fill="x", padx=10, pady=5)
        self.svatek_label = ttk.Label(frame_api, text="Načítám data...", font=("Helvetica", 12))
        self.svatek_label.pack()

        # Odpočet
        frame_countdown = ttk.LabelFrame(self.root, text="Odchod", padding=10)
        frame_countdown.pack(fill="x", padx=10, pady=10)
        self.btn_countdown = ttk.Button(frame_countdown, text="Minimální doba do odchodu (7h)", command=self.start_countdown)
        self.btn_countdown.pack(fill="x")
        self.lbl_timer = ttk.Label(frame_countdown, text="07:00:00", font=("Courier New", 24, "bold"), foreground="gray")
        self.lbl_timer.pack(pady=5)

        # Poznámka
        frame_note = ttk.Frame(self.root, padding=10)
        frame_note.pack(fill="x", side="bottom")
        
        # Tlačítko pro opětovné zobrazení připomínky
        btn_reminder = ttk.Button(frame_note, text="Co jsem to chtěl?", command=self.show_reminder)
        btn_reminder.pack(fill="x", ipady=5, pady=(0, 5))
        
        btn_note = ttk.Button(frame_note, text="Přidat poznámku na zítra", command=self.open_note_editor)
        btn_note.pack(fill="x", ipady=10)

    def update_clock(self):
        now = datetime.datetime.now()
        self.date_label.config(text=now.strftime("%d. %m. %Y"))
        self.time_label.config(text=now.strftime("%H:%M:%S"))
        self.root.after(1000, self.update_clock)

    def fetch_svatek_api(self):
        url = "https://svatkyapi.cz/api/day"
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                name = data.get("name", "Neznámé")
                day_in_week = data.get("dayInWeek", "")
                def update_ui():
                    self.svatek_label.config(text=name, foreground="blue")
                    self.day_in_week_label.config(text=day_in_week)
                self.root.after(0, update_ui)
            else:
                self.root.after(0, lambda: self.svatek_label.config(text="Chyba API"))
        except Exception as e:
            self.root.after(0, lambda: self.svatek_label.config(text="Nelze načíst data"))
            print(f"Chyba: {e}")

    def start_countdown(self):
        if not self.countdown_running:
            self.countdown_running = True
            self.btn_countdown.config(state="disabled")
            self.lbl_timer.config(foreground="red")
            self.tick_countdown()

    def tick_countdown(self):
        if self.countdown_time.total_seconds() > 0:
            self.countdown_time -= datetime.timedelta(seconds=1)
            total_seconds = int(self.countdown_time.total_seconds())
            hours, remainder = divmod(total_seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            self.lbl_timer.config(text=f"{hours:02}:{minutes:02}:{seconds:02}")
            self.root.after(1000, self.tick_countdown)
        else:
            self.lbl_timer.config(text="MŮŽEŠ JÍT DOMŮ!", foreground="green")
            messagebox.showinfo("Konec", "Je čas jít domů!")
            self.countdown_running = False

    def open_note_editor(self):
        NoteEditor(self.root, self.save_note_to_file)

    def save_note_to_file(self, content):
        try:
            with open(self.note_file, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Uloženo", "Poznámka byla uložena na příště.")
        except Exception as e:
            messagebox.showerror("Chyba", f"Nepodařilo se uložit soubor: {e}")

    def show_reminder(self):
        """Manuální zobrazení uložené poznámky"""
        if os.path.exists(self.note_file):
            try:
                with open(self.note_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    StickyNote(self.root, content)
                else:
                    messagebox.showinfo("Info", "Poznámka je prázdná.")
            except Exception as e:
                messagebox.showerror("Chyba", f"Nepodařilo se načíst poznámku: {e}")
        else:
             messagebox.showinfo("Info", "Zatím žádná poznámka neexistuje.")

    def check_existing_note(self):
        if os.path.exists(self.note_file):
            try:
                with open(self.note_file, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                if content:
                    StickyNote(self.root, content)
            except Exception:
                pass

if __name__ == "__main__":
    root = tk.Tk()
    app = WorkDayApp(root)
    root.mainloop()