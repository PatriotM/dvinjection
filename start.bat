@echo off
REM ============================================================
REM  DV + HDR => Profile 8.1 Hybrid Batch Mux  -  Starter
REM  dv_hdr_batch_mux.py muss im gleichen Ordner liegen
REM ============================================================

REM  Python-Pfad (falls nicht im PATH):
REM  set PYTHON=C:\Python312\python.exe
set PYTHON=python

echo.
echo  == DV + HDR Batch Mux ==
echo  Konfiguration direkt im .py-Script (oben, KONFIGURATION-Block)
echo.

%PYTHON% "%~dp0dv_hdr_batch_mux.py"

echo.
pause
