@echo off
title FOLab
cd /d "%~dp0"
echo Starting FOLab - the editor opens in your browser in a few seconds.
echo Keep this window open while you work; close it to stop FOLab.
py -3 app\server.py
if errorlevel 1 pause
