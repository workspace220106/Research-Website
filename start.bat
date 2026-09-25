@echo off
cd /d "%~dp0"
echo GeoResearch Studio will open at http://127.0.0.1:8765
echo Keep this window open while using the app.
echo.
py -3 server.py
if errorlevel 1 python server.py
pause
