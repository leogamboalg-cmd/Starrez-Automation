$ErrorActionPreference = "Stop"

$appName = "Add New Contacts for Newsletter"
$taskName = "Newsletter Response Notification Check"
$installDirectory = Join-Path $env:LOCALAPPDATA "Programs\$appName"
$desktopShortcut = Join-Path ([Environment]::GetFolderPath("Desktop")) "$appName.lnk"

Unregister-ScheduledTask -TaskName $taskName -Confirm:$false -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $desktopShortcut -Force -ErrorAction SilentlyContinue
Remove-Item -LiteralPath $installDirectory -Recurse -Force -ErrorAction SilentlyContinue

Write-Host "$appName was uninstalled."
