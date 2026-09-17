$ErrorActionPreference = "Stop"

$appName = "Add New Contacts for Newsletter"
$taskName = "Newsletter Response Notification Check"
$packageDirectory = Split-Path -Parent $PSScriptRoot
$sourceExe = Join-Path $packageDirectory "$appName.exe"
$installDirectory = Join-Path $env:LOCALAPPDATA "Programs\$appName"
$installedExe = Join-Path $installDirectory "$appName.exe"
$settingsDirectory = Join-Path $env:LOCALAPPDATA $appName
$settingsFile = Join-Path $settingsDirectory "launcher_settings.json"
$desktopPath = [Environment]::GetFolderPath("Desktop")
$desktopShortcut = Join-Path $desktopPath "$appName.lnk"

if (-not (Test-Path -LiteralPath $sourceExe)) {
    throw "The application executable was not found in the installation package."
}

Add-Type -AssemblyName System.Windows.Forms
$fileDialog = New-Object System.Windows.Forms.OpenFileDialog
$fileDialog.Title = "Select the shared UHS Newsletter Responses CSV file"
$fileDialog.Filter = "CSV files (*.csv)|*.csv"
$fileDialog.CheckFileExists = $true
$fileDialog.Multiselect = $false

if (Test-Path -LiteralPath $settingsFile) {
    try {
        $existingSettings = Get-Content -LiteralPath $settingsFile -Raw | ConvertFrom-Json
        $existingSharedFile = $existingSettings.shared_response_file
        if ($existingSharedFile -and (Test-Path -LiteralPath $existingSharedFile)) {
            $fileDialog.InitialDirectory = Split-Path -Parent $existingSharedFile
            $fileDialog.FileName = Split-Path -Leaf $existingSharedFile
        }
    } catch {
        $existingSettings = $null
    }
}

if ($fileDialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
    throw "Installation was cancelled because no shared responses CSV was selected."
}
$sharedResponseFile = $fileDialog.FileName

$settings = [ordered]@{}
if ($existingSettings) {
    foreach ($property in $existingSettings.PSObject.Properties) {
        $settings[$property.Name] = $property.Value
    }
}
$settings["shared_response_file"] = $sharedResponseFile
$settings["excel_file"] = $sharedResponseFile
New-Item -ItemType Directory -Path $settingsDirectory -Force | Out-Null
$settingsJson = $settings | ConvertTo-Json
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($settingsFile, $settingsJson, $utf8NoBom)

New-Item -ItemType Directory -Path $installDirectory -Force | Out-Null
Copy-Item -LiteralPath $sourceExe -Destination $installedExe -Force

$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($desktopShortcut)
$shortcut.TargetPath = $installedExe
$shortcut.WorkingDirectory = $installDirectory
$shortcut.IconLocation = "$installedExe,0"
$shortcut.Description = $appName
$shortcut.Save()

$action = New-ScheduledTaskAction -Execute $installedExe -Argument "--check-notifications"
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) `
    -RepetitionInterval (New-TimeSpan -Hours 1)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -ExecutionTimeLimit (New-TimeSpan -Minutes 2)
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger `
    -Settings $settings -Description "Checks the synced newsletter response CSV for unprocessed response IDs." `
    -Force | Out-Null

Write-Host "$appName was installed successfully."
Write-Host "Desktop shortcut: $desktopShortcut"
Write-Host "Shared responses: $sharedResponseFile"
Write-Host "Background check: once per hour"
