$ErrorActionPreference = "Stop"

# Libera a porta 8080 matando processos órfãos que possam travar o banco H2
$PortKeycloak = 8080
try {
    $Connection = Get-NetTCPConnection -LocalPort $PortKeycloak -ErrorAction SilentlyContinue
    if ($Connection) {
        $ProcessId = $Connection.OwningProcess | Select-Object -Unique
        foreach ($pid in $ProcessId) {
            if ($pid -gt 0) {
                Write-Host "Processo órfão ($pid) detectado ocupando a porta $PortKeycloak. Finalizando para destravar o banco H2..." -ForegroundColor Yellow
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host "Aviso: Não foi possível verificar ou encerrar processos na porta $PortKeycloak automaticamente." -ForegroundColor Cyan
}

$KeycloakVersion = "24.0.3"
$KeycloakUrl = "https://github.com/keycloak/keycloak/releases/download/$KeycloakVersion/keycloak-$KeycloakVersion.zip"
$ZipFile = "keycloak-$KeycloakVersion.zip"
$ExtractFolder = "keycloak-$KeycloakVersion"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Instalador Automático do Keycloak" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (!(Test-Path $ExtractFolder)) {
    if (!(Test-Path $ZipFile)) {
        Write-Host "`nBaixando o Keycloak v$KeycloakVersion... Isso pode demorar um pouco." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $KeycloakUrl -OutFile $ZipFile
        Write-Host "Download concluído!" -ForegroundColor Green
    } else {
        Write-Host "`nArquivo ZIP já encontrado: $ZipFile" -ForegroundColor Green
    }

    Write-Host "Extraindo os arquivos..." -ForegroundColor Yellow
    Expand-Archive -Path $ZipFile -DestinationPath . -Force
    Write-Host "Extração concluída!" -ForegroundColor Green
} else {
    Write-Host "`nKeycloak já está extraído na pasta: $ExtractFolder" -ForegroundColor Green
}

Write-Host "`nConfigurando credenciais do administrador Master (admin / admin)..." -ForegroundColor Yellow
$env:KEYCLOAK_ADMIN = "admin"
$env:KEYCLOAK_ADMIN_PASSWORD = "admin"

Write-Host "`nIniciando o servidor Keycloak em modo de desenvolvimento..." -ForegroundColor Cyan
Write-Host "O Realm 'buscadados' será importado automaticamente." -ForegroundColor Cyan
Write-Host "Mantenha esta janela aberta para manter o servidor rodando.`n" -ForegroundColor Yellow

$RealmPath = Resolve-Path "realm-buscadados.json"
$ImportDir = ".\$ExtractFolder\data\import"

if (!(Test-Path $ImportDir)) {
    New-Item -ItemType Directory -Force -Path $ImportDir | Out-Null
}
Copy-Item -Path $RealmPath -Destination $ImportDir -Force

$KeycloakBat = ".\$ExtractFolder\bin\kc.bat"

Write-Host "Executando: $KeycloakBat start-dev --import-realm"
& $KeycloakBat start-dev --import-realm
