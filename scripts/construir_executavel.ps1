[CmdletBinding()]
param()

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$RaizProjeto = Split-Path -Parent $PSScriptRoot
$PastaAmbienteBuild = Join-Path $RaizProjeto ".venv-build"
$PythonBuild = Join-Path $PastaAmbienteBuild "Scripts\python.exe"
$PastaNavegadores = Join-Path (
    Join-Path $RaizProjeto ".build-cache"
) "playwright-browsers"
$PastaDistribuicao = Join-Path $RaizProjeto "dist\ArboHub"
$Executavel = Join-Path $PastaDistribuicao "ArboHub.exe"
$PacoteZip = Join-Path (
    Join-Path $RaizProjeto "dist"
) "ArboHub-v0.6-windows-x64.zip"

function Invoke-PythonBuild {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$ArgumentosPython
    )

    & $PythonBuild @ArgumentosPython

    if ($LASTEXITCODE -ne 0) {
        throw (
            "Comando Python falhou com codigo " +
            "${LASTEXITCODE}: $($ArgumentosPython -join ' ')"
        )
    }
}

Push-Location $RaizProjeto
$NavegadoresAnteriores = $env:PLAYWRIGHT_BROWSERS_PATH

try {
    if (-not (Test-Path -LiteralPath $PythonBuild)) {
        py -3.14 -m venv $PastaAmbienteBuild

        if ($LASTEXITCODE -ne 0) {
            throw "Não foi possível criar o ambiente de build."
        }
    }

    Invoke-PythonBuild -ArgumentosPython @(
        "-m", "pip", "install",
        "-r", "requirements-build.txt"
    )

    $env:PLAYWRIGHT_BROWSERS_PATH = $PastaNavegadores

    Invoke-PythonBuild -ArgumentosPython @(
        "-m", "playwright", "install",
        "--no-shell", "chromium"
    )

    $PastaLinksPlaywright = Join-Path $PastaNavegadores ".links"
    if (Test-Path -LiteralPath $PastaLinksPlaywright) {
        Remove-Item `
            -LiteralPath $PastaLinksPlaywright `
            -Recurse `
            -Force
    }

    Invoke-PythonBuild -ArgumentosPython @(
        "-m", "PyInstaller",
        "--noconfirm", "--clean",
        "ArboHub.spec"
    )

    if (-not (Test-Path -LiteralPath $Executavel)) {
        throw "Executável não encontrado em $Executavel"
    }

    & $Executavel --verificar-distribuicao
    if ($LASTEXITCODE -ne 0) {
        throw "A distribuição gerada não passou na verificação."
    }

    if (Test-Path -LiteralPath $PacoteZip) {
        Remove-Item -LiteralPath $PacoteZip -Force
    }

    Compress-Archive `
        -Path (Join-Path $PastaDistribuicao "*") `
        -DestinationPath $PacoteZip `
        -CompressionLevel Optimal

    $Hash = Get-FileHash `
        -LiteralPath $PacoteZip `
        -Algorithm SHA256

    Write-Host ""
    Write-Host "Build concluido e verificado."
    Write-Host "Executavel: $Executavel"
    Write-Host "Pacote: $PacoteZip"
    Write-Host "SHA-256: $($Hash.Hash)"
}
finally {
    if ($null -eq $NavegadoresAnteriores) {
        Remove-Item `
            Env:PLAYWRIGHT_BROWSERS_PATH `
            -ErrorAction SilentlyContinue
    }
    else {
        $env:PLAYWRIGHT_BROWSERS_PATH = $NavegadoresAnteriores
    }

    Pop-Location
}
