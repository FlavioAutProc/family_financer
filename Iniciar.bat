@echo off
chcp 65001 >nul
title Orçamento Familiar Pro
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo.
  echo  [!] O Python não foi encontrado neste computador.
  echo      Instale em https://www.python.org/downloads/  ^(marque "Add Python to PATH"^) e abra este arquivo de novo.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo  Primeira vez: preparando o sistema ^(leva alguns minutos^)...
  python -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet
  if errorlevel 1 (
    echo  [!] Não foi possível instalar. Verifique a internet e tente de novo.
    pause
    exit /b 1
  )
)

echo.
echo  Abrindo o Orçamento Familiar Pro no navegador...
echo  ^(para encerrar, feche esta janela^)
echo.
".venv\Scripts\python.exe" -m streamlit run app.py
pause
