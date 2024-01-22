Push-Location
Set-Location $PSScriptRoot

$base_path = "..\src\hydra"

#Get version from __init__.py
if (Get-Content "$base_path\__init__.py" | Where-Object { $_ -match "version.*?(\d,\s*\d,\s*\d)" }) {
    $version = $Matches[1] -replace '\s*,\s*',"."
    $name = "Hydra_$version.zip"
    Write-Host "Found version number: $version"
}
else {
    Pop-Location
    Write-Error "Addon is missing a version number!" -ErrorAction Stop
}

$null = New-Item "Hydra" -ItemType "Directory"
Copy-Item "$base_path\*" "Hydra" -Recurse

Get-ChildItem Hydra -Filter __pycache__ -Recurse | Remove-Item -Recurse

Compress-Archive -Path "Hydra" -DestinationPath "..\bin\$name" -CompressionLevel Optimal -Force
Write-Host "Created archive $name in /bin folder."

Remove-Item Hydra -Recurse
Pop-Location