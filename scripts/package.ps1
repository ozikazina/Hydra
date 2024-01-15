Push-Location
Set-Location $PSScriptRoot

#Get version from __init__.py
if (Get-Content ..\addon\__init__.py | Where-Object { $_ -match "version.*?(\d,\s*\d,\s*\d)" }) {
    $version = $Matches[1] -replace '\s*,\s*',"."
    $name = "Hydra_$version.zip"
    Write-Host "Found version number: $version"
}
else {
    Pop-Location
    Write-Error "Addon is missing a version number!" -ErrorAction Stop
}

$null = New-Item "Hydra" -ItemType "Directory"
Copy-Item "..\addon\*" "Hydra" -Recurse

Get-ChildItem Hydra -Filter __pycache__ -Recurse | Remove-Item -Recurse

Compress-Archive -Path "Hydra" -DestinationPath "..\bin\$name" -CompressionLevel Optimal -Force
Write-Host "Created archive $name in /bin folder."

Remove-Item Hydra -Recurse
Pop-Location