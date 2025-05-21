@echo off
:loop
python check_targets.py
timeout /t 60
goto loop
