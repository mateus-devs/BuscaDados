$ErrorActionPreference = "Stop"

# =============================================================================
# CONFIGURAÇÕES DO BANCO DE DADOS (lidas do .env do projeto)
# =============================================================================
$EnvFile = ".\.env"
$DbHost     = "localhost"
$DbPort     = "5432"
$DbName     = "keycloak"
$DbUser     = "postgres"
$DbPassword = ""

# Lê a senha do .env para não duplicar credenciais
if (Test-Path $EnvFile) {
    $envLines = Get-Content $EnvFile
    foreach ($line in $envLines) {
        if ($line -match "^DB_PASSWORD=(.+)$") {
            $DbPassword = $Matches[1].Trim()
        }
        if ($line -match "^DB_HOST=(.+)$") {
            $DbHost = $Matches[1].Trim()
        }
        if ($line -match "^DB_PORT=(.+)$") {
            $DbPort = $Matches[1].Trim()
        }
    }
}

# =============================================================================
# LIBERA A PORTA 8080 (mata processos Java órfãos)
# =============================================================================
$PortKeycloak = 8080
try {
    $Connection = Get-NetTCPConnection -LocalPort $PortKeycloak -ErrorAction SilentlyContinue
    if ($Connection) {
        $ProcessId = $Connection.OwningProcess | Select-Object -Unique
        foreach ($pid in $ProcessId) {
            if ($pid -gt 0) {
                Write-Host "Processo orfao ($pid) detectado na porta $PortKeycloak. Finalizando..." -ForegroundColor Yellow
                Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Seconds 2
    }
} catch {
    Write-Host "Aviso: Nao foi possivel verificar processos na porta $PortKeycloak." -ForegroundColor Cyan
}

# =============================================================================
# CRIA O BANCO 'keycloak' NO POSTGRESQL SE NAO EXISTIR
# =============================================================================
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Verificando banco de dados PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# Detecta o psql.exe (suporta PG 14, 15, 16, 17)
$PsqlExe = $null
foreach ($ver in @("17", "16", "15", "14")) {
    $candidate = "C:\Program Files\PostgreSQL\$ver\bin\psql.exe"
    if (Test-Path $candidate) {
        $PsqlExe = $candidate
        break
    }
}

if (-not $PsqlExe) {
    Write-Host "AVISO: psql.exe nao encontrado em C:\Program Files\PostgreSQL\*\bin\psql.exe" -ForegroundColor Yellow
    Write-Host "Assumindo que o banco '$DbName' ja existe. Se o Keycloak falhar, crie manualmente:" -ForegroundColor Yellow
    Write-Host "  CREATE DATABASE $DbName;" -ForegroundColor Cyan
} else {
    $env:PGPASSWORD = $DbPassword
    $psqlCheck = & $PsqlExe -h $DbHost -p $DbPort -U $DbUser -lqt 2>&1

    if ("$psqlCheck" -match "\b$DbName\b") {
        Write-Host "Banco '$DbName' ja existe no PostgreSQL. OK!" -ForegroundColor Green
    } else {
        Write-Host "Criando banco '$DbName' no PostgreSQL..." -ForegroundColor Yellow
        & $PsqlExe -h $DbHost -p $DbPort -U $DbUser -c "CREATE DATABASE $DbName ENCODING 'UTF8';" 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "Banco '$DbName' criado com sucesso!" -ForegroundColor Green
        } else {
            Write-Host "ERRO: Falha ao criar o banco '$DbName'." -ForegroundColor Red
            Write-Host "Crie manualmente: CREATE DATABASE $DbName;" -ForegroundColor Cyan
            pause
            exit 1
        }
    }
    $env:PGPASSWORD = ""
}

# =============================================================================
# INSTALAÇÃO / EXTRAÇÃO DO KEYCLOAK
# =============================================================================
$KeycloakVersion = "24.0.3"
$KeycloakUrl = "https://github.com/keycloak/keycloak/releases/download/$KeycloakVersion/keycloak-$KeycloakVersion.zip"
$ZipFile = "keycloak-$KeycloakVersion.zip"
$ExtractFolder = "keycloak-$KeycloakVersion"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Instalador do Keycloak v$KeycloakVersion" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

if (!(Test-Path $ExtractFolder)) {
    if (!(Test-Path $ZipFile)) {
        Write-Host "`nBaixando o Keycloak v$KeycloakVersion..." -ForegroundColor Yellow
        Invoke-WebRequest -Uri $KeycloakUrl -OutFile $ZipFile
        Write-Host "Download concluido!" -ForegroundColor Green
    } else {
        Write-Host "`nArquivo ZIP ja encontrado: $ZipFile" -ForegroundColor Green
    }
    Write-Host "Extraindo os arquivos..." -ForegroundColor Yellow
    Expand-Archive -Path $ZipFile -DestinationPath . -Force
    Write-Host "Extracao concluida!" -ForegroundColor Green
} else {
    Write-Host "`nKeycloak ja esta extraido em: $ExtractFolder" -ForegroundColor Green
}

# =============================================================================
# IMPORTAÇÃO DO REALM
# =============================================================================
$RealmPath = Resolve-Path "realm-buscadados.json"
$ImportDir = ".\$ExtractFolder\data\import"

if (!(Test-Path $ImportDir)) {
    New-Item -ItemType Directory -Force -Path $ImportDir | Out-Null
}
Copy-Item -Path $RealmPath -Destination $ImportDir -Force

# =============================================================================
# INICIALIZAÇÃO DO KEYCLOAK COM POSTGRESQL
# =============================================================================
Write-Host "`nConfigurando credenciais do administrador Master..." -ForegroundColor Yellow
$env:KEYCLOAK_ADMIN = "admin"
$env:KEYCLOAK_ADMIN_PASSWORD = "admin"

# Credenciais do PostgreSQL passadas também via variável de ambiente (reforço ao keycloak.conf)
$env:KC_DB          = "postgres"
$env:KC_DB_URL      = "jdbc:postgresql://${DbHost}:${DbPort}/$DbName"
$env:KC_DB_USERNAME = $DbUser
$env:KC_DB_PASSWORD = $DbPassword

$KeycloakBat = ".\$ExtractFolder\bin\kc.bat"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Iniciando Keycloak com PostgreSQL" -ForegroundColor Green
Write-Host "  Banco: $DbName @ ${DbHost}:${DbPort}" -ForegroundColor Green
Write-Host "  SEM H2! Dados persistem entre reinicializacoes." -ForegroundColor Green
Write-Host "  Realm 'buscadados' sera importado automaticamente." -ForegroundColor Green
Write-Host "  Mantenha esta janela aberta." -ForegroundColor Yellow
Write-Host "========================================`n" -ForegroundColor Green

Write-Host "Executando: $KeycloakBat start-dev --import-realm"
& $KeycloakBat start-dev --import-realm
