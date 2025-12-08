import tkinter as tk
from tkinter import ttk, messagebox
from tkcalendar import Calendar
import json
import os
from datetime import datetime, timedelta
import uuid

# --- KONFIGURACE A DATA ---
DATA_FILE = "tasks.json"

class TaskManager:
    """Třída pro správu dat (načítání/ukládání JSON) a logiku priorit"""
    def __init__(self):
        self.tasks = self.load_tasks()
        self.cleanup_old_completed_tasks()
        # 2) Kontrola priorit při spuštění
        self.check_startup_priorities()

    def load_tasks(self):
        if not os.path.exists(DATA_FILE):
            return []
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def save_tasks(self):
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tasks, f, indent=4, ensure_ascii=False)

    def add_task(self, title, deadline, priority, description=""):
        new_task = {
            "id": str(uuid.uuid4()),
            "title": title,
            "deadline": deadline, 
            "priority": int(priority),
            "description": description,
            "subtasks": [],
            "completed_date": None 
        }
        self.tasks.append(new_task)
        self.save_tasks()

    def update_task(self, task_data):
        for i, task in enumerate(self.tasks):
            if task["id"] == task_data["id"]:
                self.tasks[i] = task_data
                break
        self.save_tasks()

    def delete_task(self, task_id):
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        # 1) Po odstranění tasku přepočítat priority ostatním
        self.recalc_priorities_after_change()
        self.save_tasks()

    def mark_as_completed(self, task_id):
        for task in self.tasks:
            if task["id"] == task_id:
                task["completed_date"] = datetime.now().strftime("%Y-%m-%d")
                break
        # 1) Po splnění tasku přepočítat priority ostatním
        self.recalc_priorities_after_change()
        self.save_tasks()

    def cleanup_old_completed_tasks(self):
        today = datetime.now().date()
        tasks_to_keep = []
        modified = False
        
        for task in self.tasks:
            if task.get("completed_date"):
                try:
                    comp_date = datetime.strptime(task["completed_date"], "%Y-%m-%d").date()
                    if (today - comp_date).days <= 31:
                        tasks_to_keep.append(task)
                    else:
                        modified = True
                except ValueError:
                    tasks_to_keep.append(task)
            else:
                tasks_to_keep.append(task)
        
        if modified:
            self.tasks = tasks_to_keep
            self.save_tasks()

    # --- NOVÁ LOGIKA ---
    
    def check_startup_priorities(self):
        """Logika při startu aplikace"""
        changed = False
        for task in self.tasks:
            # Ignorovat splněné
            if task.get("completed_date"):
                continue
            
            days = days_remaining(task['deadline'])
            
            # Po deadline -> priorita 15
            if days < 0:
                if task['priority'] != 15:
                    task['priority'] = 15
                    changed = True
            
            # Méně než 2 dny -> priorita min. 13
            elif days < 2:
                if task['priority'] < 13:
                    task['priority'] = 13
                    changed = True
        
        if changed:
            self.save_tasks()

    def recalc_priorities_after_change(self):
        """Logika po splnění/smazání: < 10 dní -> priorita +2 (max 15)"""
        changed = False
        for task in self.tasks:
            if task.get("completed_date"):
                continue

            days = days_remaining(task['deadline'])
            
            if days < 10:
                old_prio = task['priority']
                # Zvyšujeme pouze pokud ještě není 15 nebo víc
                if old_prio < 15:
                    new_prio = min(15, old_prio + 2)
                    if new_prio != old_prio:
                        task['priority'] = new_prio
                        changed = True
        
        # Poznámka: self.save_tasks() se volá v parent metodě (delete/mark_as_completed),
        # ale pro jistotu, pokud by se volalo odjinud:
        # (Zde to nevadí, data jsou v paměti a uloží se o krok dál)

# --- POMOCNÉ FUNKCE ---
def get_priority_color(priority):
    p = max(1, min(20, int(priority)))
    if p <= 10:
        r = int(255 * (p / 10))
        g = 255
        b = 0
    else:
        r = 255
        g = int(255 * ((20 - p) / 10))
        b = 0
    return f'#{r:02x}{g:02x}{b:02x}'

def days_remaining(deadline_str):
    try:
        deadline = datetime.strptime(deadline_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        delta = (deadline - today).days
        return delta
    except ValueError:
        return 0

# --- GUI: DETAIL OKNO ---
class TaskDetailWindow(tk.Toplevel):
    def __init__(self, parent, task_data, manager, refresh_callback):
        super().__init__(parent)
        self.title(f"Detail: {task_data['title']}")
        self.geometry("500x650")
        self.task_data = task_data
        self.manager = manager
        self.refresh_callback = refresh_callback
        
        self.is_completed = task_data.get("completed_date") is not None
        
        # --- GUI Elements ---
        tk.Label(self, text="Název úkolu:").pack(pady=5)
        self.title_entry = tk.Entry(self, width=50)
        self.title_entry.insert(0, task_data['title'])
        self.title_entry.pack()

        # --- SEKCE DATUM ---
        tk.Label(self, text="Deadline:").pack(pady=5)
        date_frame = tk.Frame(self)
        date_frame.pack()
        self.deadline_entry = tk.Entry(date_frame, width=15, justify="center")
        self.deadline_entry.insert(0, task_data['deadline'])
        self.deadline_entry.pack(side=tk.LEFT, padx=5)
        
        self.cal_btn = tk.Button(date_frame, text="📅 Vybrat datum", command=self.open_calendar_popup)
        self.cal_btn.pack(side=tk.LEFT)

        tk.Label(self, text="Priorita (1-20):").pack(pady=5)
        self.prio_scale = tk.Scale(self, from_=1, to=20, orient=tk.HORIZONTAL)
        self.prio_scale.set(task_data['priority'])
        self.prio_scale.pack()

        tk.Label(self, text="Popis:").pack(pady=5)
        self.desc_text = tk.Text(self, height=5, width=50)
        self.desc_text.insert("1.0", task_data.get('description', ''))
        self.desc_text.pack()

        tk.Label(self, text="Podúkoly:").pack(pady=10)
        
        self.subtasks_frame = tk.Frame(self)
        self.subtasks_frame.pack(fill="both", expand=True, padx=20)
        self.subtask_vars = []
        self.render_subtasks()

        self.add_frame = tk.Frame(self)
        self.add_frame.pack(pady=5)
        self.new_sub_entry = tk.Entry(self.add_frame, width=30)
        self.new_sub_entry.pack(side=tk.LEFT)
        self.add_btn = tk.Button(self.add_frame, text="+", command=self.add_subtask)
        self.add_btn.pack(side=tk.LEFT)

        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=20, fill="x")
        
        self.save_btn = tk.Button(btn_frame, text="Uložit změny", bg="#ccffcc", command=self.save_changes)
        self.save_btn.pack(side=tk.RIGHT, padx=10)
        
        tk.Button(btn_frame, text="Smazat úkol", bg="#ffcccc", command=self.delete_task).pack(side=tk.LEFT, padx=10)

        if self.is_completed:
            self.disable_editing()

    def disable_editing(self):
        self.title_entry.config(state='disabled')
        self.deadline_entry.config(state='disabled')
        self.cal_btn.config(state='disabled')
        self.prio_scale.config(state='disabled')
        self.desc_text.config(state='disabled')
        self.new_sub_entry.config(state='disabled')
        self.add_btn.config(state='disabled')
        self.save_btn.pack_forget()

    def open_calendar_popup(self):
        top = tk.Toplevel(self)
        top.title("Vyber datum")
        top.geometry("300x250")
        try:
            current_date_str = self.deadline_entry.get()
            current_date = datetime.strptime(current_date_str, "%Y-%m-%d").date()
        except ValueError:
            current_date = datetime.now().date()

        cal = Calendar(top, selectmode='day', 
                       year=current_date.year, month=current_date.month, day=current_date.day,
                       date_pattern='yyyy-mm-dd')
        cal.pack(pady=20, padx=20, fill="both", expand=True)

        def set_date_and_close(event=None):
            self.deadline_entry.delete(0, tk.END)
            self.deadline_entry.insert(0, cal.get_date())
            top.destroy()
        cal.bind("<<CalendarSelected>>", set_date_and_close)

    def render_subtasks(self):
        for widget in self.subtasks_frame.winfo_children():
            widget.destroy()
        self.subtask_vars = []
        
        for i, sub in enumerate(self.task_data.get("subtasks", [])):
            var = tk.BooleanVar(value=sub["done"])
            self.subtask_vars.append(var)
            
            f = tk.Frame(self.subtasks_frame)
            f.pack(fill="x", anchor="w")
            
            state = "disabled" if self.is_completed else "normal"
            cb = tk.Checkbutton(f, text=sub["text"], variable=var, state=state)
            cb.pack(side=tk.LEFT)
            
            if not self.is_completed:
                tk.Button(f, text="x", font=("Arial", 8), fg="red", relief="flat", 
                          command=lambda idx=i: self.remove_subtask(idx)).pack(side=tk.RIGHT)

    def add_subtask(self):
        text = self.new_sub_entry.get()
        if text:
            self.task_data["subtasks"].append({"text": text, "done": False})
            self.new_sub_entry.delete(0, tk.END)
            self.render_subtasks()

    def remove_subtask(self, index):
        del self.task_data["subtasks"][index]
        self.render_subtasks()

    def save_changes(self):
        self.task_data['title'] = self.title_entry.get()
        self.task_data['deadline'] = self.deadline_entry.get()
        self.task_data['priority'] = self.prio_scale.get()
        self.task_data['description'] = self.desc_text.get("1.0", tk.END).strip()
        
        for i, var in enumerate(self.subtask_vars):
            if i < len(self.task_data["subtasks"]):
                self.task_data["subtasks"][i]["done"] = var.get()

        self.manager.update_task(self.task_data)
        self.refresh_callback()
        self.destroy()

    def delete_task(self):
        if messagebox.askyesno("Smazat", "Opravdu smazat tento úkol?"):
            self.manager.delete_task(self.task_data["id"])
            self.refresh_callback()
            self.destroy()

# --- GUI: HLAVNÍ OKNO ---
class TaskApp(tk.Frame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.manager = TaskManager()
        self.pack(fill="both", expand=True)
        
        header = tk.Frame(self)
        header.pack(fill="x", pady=10, padx=10)
        tk.Label(header, text="Task Priority Solver", font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        tk.Button(header, text="+ Nový úkol", bg="lightblue", command=self.create_new_task).pack(side=tk.RIGHT)

        self.canvas = tk.Canvas(self)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Aby se grid roztáhl přes celou šířku canvasu
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(self.canvas.find_all()[0], width=e.width))

        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.refresh_list()

    def configure_grid_columns(self, container):
        """Nastaví pevné šířky sloupců pro zarovnání tabulky"""
        container.grid_columnconfigure(0, weight=0, minsize=50) # Prio
        container.grid_columnconfigure(1, weight=1)             # Nazev
        container.grid_columnconfigure(2, weight=0, minsize=100)# Deadline
        container.grid_columnconfigure(3, weight=0, minsize=100)# Zbyva
        container.grid_columnconfigure(4, weight=0, minsize=50) # Akce

    def refresh_list(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        tasks = self.manager.tasks
        active_tasks = [t for t in tasks if not t.get("completed_date")]
        completed_tasks = [t for t in tasks if t.get("completed_date")]

        active_tasks.sort(key=lambda x: (x['priority'], -days_remaining(x['deadline'])), reverse=True)
        completed_tasks.sort(key=lambda x: x['completed_date'], reverse=True)

        # --- HLAVIČKA ---
        self.create_headers()
        
        if not active_tasks:
            tk.Label(self.scrollable_frame, text="Žádné aktivní úkoly", fg="grey").pack(pady=10)
        
        for task in active_tasks:
            self.create_task_row(task, is_completed=False)

        # --- ODĚLOVAČ ---
        if completed_tasks:
            sep = tk.Frame(self.scrollable_frame, height=2, bg="black")
            sep.pack(fill="x", pady=(20, 5))
            tk.Label(self.scrollable_frame, text="Splněné úkoly (posledních 31 dní)", 
                     font=("Arial", 10, "italic")).pack(anchor="w", padx=5)

        for task in completed_tasks:
            self.create_task_row(task, is_completed=True)

    def create_headers(self):
        headers_frame = tk.Frame(self.scrollable_frame)
        headers_frame.pack(fill="x", pady=2, padx=5)
        
        self.configure_grid_columns(headers_frame)
        
        tk.Label(headers_frame, text="Prio", font="bold").grid(row=0, column=0, sticky="w")
        tk.Label(headers_frame, text="Název úkolu", font="bold").grid(row=0, column=1, sticky="w")
        tk.Label(headers_frame, text="Deadline", font="bold").grid(row=0, column=2)
        tk.Label(headers_frame, text="Zbývá", font="bold").grid(row=0, column=3)
        tk.Label(headers_frame, text="Akce", font="bold").grid(row=0, column=4)

    def create_task_row(self, task, is_completed):
        if is_completed:
            color = "#d3d3d3"
            fg_color = "#666666"
            relief = "flat"
        else:
            color = get_priority_color(task['priority'])
            fg_color = "black"
            relief = "raised"

        days = days_remaining(task['deadline'])
        
        row = tk.Frame(self.scrollable_frame, bg=color, pady=5, padx=5, bd=1, relief=relief)
        row.pack(fill="x", pady=2, padx=5)
        
        self.configure_grid_columns(row)

        def on_click(e):
            TaskDetailWindow(self.parent, task, self.manager, self.refresh_list)

        l_prio = tk.Label(row, text=str(task['priority']), bg=color, fg=fg_color)
        l_prio.grid(row=0, column=0, sticky="nsew")
        
        l_title = tk.Label(row, text=task['title'], bg=color, fg=fg_color, anchor="w", font=("Arial", 10, "bold"))
        l_title.grid(row=0, column=1, sticky="nsew")
        
        l_dead = tk.Label(row, text=task['deadline'], bg=color, fg=fg_color)
        l_dead.grid(row=0, column=2, sticky="nsew")
        
        days_text = f"{days} dní" if not is_completed else task["completed_date"]
        l_days = tk.Label(row, text=days_text, bg=color, fg=fg_color)
        l_days.grid(row=0, column=3, sticky="nsew")

        # Tlačítko AKCE
        action_container = tk.Frame(row, bg=color) 
        action_container.grid(row=0, column=4, sticky="nsew")
        
        if not is_completed:
            btn_done = tk.Button(action_container, text="✔", bg="white", fg="green", font=("Arial", 9, "bold"),
                                 width=3, command=lambda: self.try_complete_task(task))
            btn_done.pack(expand=True)
        else:
            tk.Label(action_container, text="✓", bg=color, fg="green", font=("Arial", 12, "bold")).pack(expand=True)

        for widget in (row, l_prio, l_title, l_dead, l_days, action_container):
            widget.bind("<Button-1>", on_click)
            widget.configure(cursor="hand2")

    def try_complete_task(self, task):
        subtasks = task.get("subtasks", [])
        if subtasks:
            not_done = [s for s in subtasks if not s["done"]]
            if not_done:
                messagebox.showwarning("Nelze splnit", "Nemáte hotové všechny podúkoly!")
                return
        
        if messagebox.askyesno("Dokončit", f"Opravdu označit úkol '{task['title']}' jako splněný?"):
            self.manager.mark_as_completed(task["id"])
            self.refresh_list()

    def create_new_task(self):
        dummy_task = {
            "id": str(uuid.uuid4()),
            "title": "Nový úkol",
            "deadline": datetime.now().strftime("%Y-%m-%d"),
            "priority": 10,
            "description": "",
            "subtasks": [],
            "completed_date": None
        }
        self.manager.tasks.append(dummy_task)
        self.manager.save_tasks()
        self.refresh_list()
        TaskDetailWindow(self.parent, dummy_task, self.manager, self.refresh_list)

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Task Priority Solver")
    root.geometry("700x600")
    app = TaskApp(root)
    root.mainloop()