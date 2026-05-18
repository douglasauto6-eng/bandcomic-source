@echo off
cd /d "%~dp0"
python bandcomic_importer_windows.py
if errorlevel 1 pause
