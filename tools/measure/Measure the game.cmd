@echo off
rem FOLab: measure where the running game spends its time. Windows' own recorder (wpr), nothing changed in the game.
rem Run it while the game is running; it asks for admin rights (Windows' recorder needs them).
net session >nul 2>&1
if errorlevel 1 (
  powershell -NoProfile -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
  exit /b
)
title FOLab: measuring the game
set "OUT=%USERPROFILE%\Documents\FOLab measurements"
if not exist "%OUT%" mkdir "%OUT%"
for /f %%t in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd-HHmmss"') do set "STAMP=%%t"
set "ETL=%OUT%\game-%STAMP%.etl"

tasklist /fi "imagename eq FalloutNV.exe" | find /i "FalloutNV.exe" >nul
if errorlevel 1 (
  echo The game isn't running. Start it, load your save, stand where it is slow, then run this again.
  pause
  exit /b
)

wpr -cancel >nul 2>&1
echo.
echo When you're standing where the game is slow, press a key here, then go straight back into the game.
echo Recording starts 15 seconds after the key (one beep) and lasts 60 seconds (two beeps at the end).
echo Walk around as you normally would; don't open the Pip-Boy or the menu.
echo.
pause
timeout /t 15 /nobreak >nul
wpr -start CPU -start "%~dp0frames.wprp!Frames.Verbose" -filemode
if errorlevel 1 (
  echo Windows' recorder didn't start. Nothing was changed.
  pause
  exit /b
)
powershell -NoProfile -Command "[console]::Beep(880,400)"
timeout /t 60 /nobreak >nul
powershell -NoProfile -Command "[console]::Beep(660,250); [console]::Beep(660,250)"
echo Saving the recording (this can take a minute)...
wpr -stop "%ETL%" "FOLab game measurement" -skipPdbGen
echo.
echo Done: %ETL%
echo Tell Claude it's done; you can close this window.
pause
