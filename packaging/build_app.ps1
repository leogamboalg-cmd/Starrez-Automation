$ErrorActionPreference = "Stop"

$packagingDirectory = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $packagingDirectory
$pythonPath = Join-Path $projectRoot ".venv\Scripts\python.exe"
$specPath = Join-Path $packagingDirectory "Add_New_Contacts_for_Newsletter.spec"

if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw "The project virtual environment was not found at $pythonPath"
}

Push-Location $projectRoot
try {
    & $pythonPath -m PyInstaller --noconfirm --clean $specPath
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}

$appPath = Join-Path $projectRoot "dist\Add New Contacts for Newsletter.exe"
$zipPath = Join-Path $projectRoot "dist\Add New Contacts for Newsletter.zip"
$distributionFiles = @(
    $appPath,
    (Join-Path $projectRoot "installer\Install Newsletter App.cmd"),
    (Join-Path $projectRoot "installer\Uninstall Newsletter App.cmd"),
    (Join-Path $projectRoot "installer\scripts"),
    (Join-Path $projectRoot "docs\START HERE - Installation Guide.html")
)
Compress-Archive -LiteralPath $distributionFiles -DestinationPath $zipPath `
    -CompressionLevel Optimal -Force
Write-Host "Built app: $appPath"
Write-Host "Built installer package: $zipPath"
