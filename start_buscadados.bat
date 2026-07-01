@echo off
title Launcher BuscaDados
color 0A

echo ==================================================
echo         INICIANDO O SISTEMA BUSCADADOS
echo ==================================================
echo [0/2] Limpando processos antigos em segundo plano para liberar portas...
:: Garante que nenhuma instância órfã do Keycloak (Java) ou Streamlit (Python) esteja rodando
taskkill /F /IM java.exe /T > nul 2>&1
wmic process where "name='python.exe' and commandline like '%%streamlit%%'" call terminate > nul 2>&1
timeout /t 2 /nobreak > nul

:: Limpa arquivos de banco de dados temporários e bloqueios (.lock.db) do H2
rmdir /s /q ".\keycloak-24.0.3\data\h2" > nul 2>&1

echo.
echo [1/2] Iniciando o Servidor de Seguranca (Keycloak)...
:: O comando 'start' abre uma nova janela do CMD separada para o Keycloak
start "Servidor_Keycloak" powershell -ExecutionPolicy Bypass -File .\instalar_keycloak.ps1

echo.
echo Aguardando 10 segundos para o Keycloak respirar e criar o banco...
timeout /t 10 /nobreak > nul

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
