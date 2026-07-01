@echo off
title Launcher BuscaDados
color 0A

echo ==================================================
echo         INICIANDO O SISTEMA BUSCADADOS
echo ==================================================
echo [0/2] Limpando processos antigos em segundo plano para liberar portas...
:: Garante que nenhuma instancia orfao do Keycloak (Java) ou Streamlit (Python) esteja rodando
taskkill /F /IM java.exe /T > nul 2>&1
powershell -Command "try { $c = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue; if ($c) { Stop-Process -Id ($c.OwningProcess | Select -Unique) -Force -ErrorAction SilentlyContinue } } catch {}" > nul 2>&1
wmic process where "name='python.exe' and commandline like '%%streamlit%%'" call terminate > nul 2>&1
timeout /t 2 /nobreak > nul

:: Keycloak agora usa PostgreSQL -- pasta h2 nao existe mais, nada para limpar.

echo.
echo [1/2] Iniciando o Servidor de Seguranca (Keycloak)...
:: O comando 'start' abre uma nova janela do CMD separada para o Keycloak
start "Servidor_Keycloak" powershell -ExecutionPolicy Bypass -File .\instalar_keycloak.ps1

echo.
echo Aguardando 15 segundos para o Keycloak conectar ao PostgreSQL e subir...
timeout /t 15 /nobreak > nul

echo.
echo [2/2] Iniciando o Aplicativo Front-End (Streamlit)...
:: O comando 'start' abre outra janela separada rodando o python do ambiente virtual
start "App_Streamlit" cmd /c ".\venv\Scripts\streamlit.exe run app.py"

echo.
echo ==================================================
echo  SUCESSO! O sistema esta rodando em segundo plano.
echo  Pode fechar esta janelinha.
echo ==================================================
timeout /t 5 > nul
