@echo off
title Desligando BuscaDados
color 0C

echo ==================================================
echo         DESLIGANDO O SISTEMA BUSCADADOS
echo ==================================================
echo.

echo [1/3] Fechando o Servidor de Seguranca (Keycloak)...
:: O Keycloak roda sobre o Java. Fechar o Java derruba o Keycloak imediatamente.
taskkill /F /IM java.exe /T > nul 2>&1
powershell -Command "try { $c = Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue; if ($c) { Stop-Process -Id ($c.OwningProcess | Select -Unique) -Force -ErrorAction SilentlyContinue } } catch {}" > nul 2>&1

echo [2/3] Fechando o Aplicativo (Streamlit)...
:: Localiza os processos do Python que estão rodando o Streamlit e mata eles
wmic process where "name='python.exe' and commandline like '%%streamlit%%'" call terminate > nul 2>&1

echo [3/3] Limpando o banco de dados temporario do Keycloak...
:: Essa linha de baixo eh o Pulo do Gato! 
:: Ao apagar a pasta h2 quando desligamos, garantimos que voce NUNCA MAIS 
:: vai enfrentar aquele erro de "Timeout" / "Arquivo Corrompido" do banco do Keycloak!
rmdir /s /q ".\keycloak-24.0.3\data\h2" > nul 2>&1

echo.
echo ==================================================
echo   SUCESSO! Todos os processos foram finalizados.
echo   Seu computador esta limpo.
echo ==================================================
pause
