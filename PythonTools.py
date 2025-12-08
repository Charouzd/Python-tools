import subprocess
import sys
import os

def install_requirements():
    print("Instaluji zavislosti z requirements.txt...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    except subprocess.CalledProcessError:
        print("Chyba pri instalaci knihoven. Pokracuji...")

def run_scripts():
    print("Spoustim aplikace...")
    
    # Cesta k interpretu Pythonu
    python_exe = sys.executable

    # Spuštění skriptů jako samostatné procesy
    # Na Windows používáme creationflags, aby se otevřela nová okna (pokud je to potřeba)
    if os.name == 'nt': # Windows
        subprocess.Popen([python_exe, "date_reminder.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
        subprocess.Popen([python_exe, "taks_priority_solver.py"], creationflags=subprocess.CREATE_NEW_CONSOLE)
    else: # Mac / Linux
        subprocess.Popen([python_exe, "date_reminder.py"])
        subprocess.Popen([python_exe, "taks_priority_solver.py"])

if __name__ == "__main__":
    # 1. Zkontroluje a nainstaluje requirements
    if os.path.exists("requirements.txt"):
        install_requirements()
    else:
        print("Soubor requirements.txt nenalezen, preskakuji instalaci.")

    # 2. Spustí oba skripty
    run_scripts()