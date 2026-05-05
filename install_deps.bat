@echo off
title SMD Dashboard - Instalador de Dependencias
echo ============================================================
echo   SMD Dashboard - Configurando Ambiente Python
echo ============================================================
echo.

echo [+] Verificando instalacao do Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [X] Python nao encontrado! 
    echo     Por favor, instale o Python 3.10 ou superior em python.org
    echo     Certifique-se de marcar a opcao "Add Python to PATH" durante a instalacao.
    pause
    exit /b
)

echo [+] Instalando bibliotecas necessarias (Pandas, OpenPyXL, LXML)...
python -m pip install --upgrade pip
python -m pip install pandas openpyxl lxml

if %errorlevel% equ 0 (
    echo.
    echo ============================================================
    echo [!] SUCESSO: Ambiente configurado com exito.
    echo     Agora voce pode rodar o dashboard usando:
    echo     python smd_merge.py --auto
    echo ============================================================
) else (
    echo.
    echo [X] Erro durante a instalacao das dependencias.
    echo     Verifique sua conexao com a internet ou permissoes de usuario.
)

echo.
pause
