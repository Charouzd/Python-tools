@echo off
echo ==========================================
echo Kontrola a instalace potrebnych knihoven...
echo ==========================================

:: 1. Nainstaluje knihovny ze souboru requirements.txt
pip install -r requirements.txt

echo.
echo ==========================================
echo Spoustim aplikace...
echo ==========================================

:: 2. Spustí první skript (date_reminder.py) v novém okně
start "Date Reminder" python date_reminder.py

:: 3. Spustí druhý skript (taks_priority_solver.py) v novém okně
:: Poznámka: Ve screenshotu máš překlep "taks", nechal jsem to tak, aby to fungovalo.
start "Priority Solver" python taks_priority_solver.py

echo Hotovo! Aplikace bezi.
pause