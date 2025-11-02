# create_portable_package.ps1
Write-Host "=== CREATING PORTABLE PACKAGE FROM WORKING BUILD ===" -ForegroundColor Green

# Check if build exists
if (-not (Test-Path "dist\ClinicalLabSoftware.exe")) {
    Write-Host "ERROR: No executable found! Run build_final_complete_fixed.ps1 first." -ForegroundColor Red
    exit 1
}

Write-Host "Found working build - creating portable package..." -ForegroundColor Cyan

$portableDir = "ClinicalLabSoftware_Portable"
if (Test-Path $portableDir) { 
    Remove-Item -Recurse -Force $portableDir
    Write-Host "Cleaned existing directory" -ForegroundColor Yellow
}

# Create portable directory
New-Item -ItemType Directory -Path $portableDir | Out-Null

Write-Host "`nCopying application files..." -ForegroundColor White

# Copy the entire dist folder contents (this is crucial!)
Write-Host "Copying distribution files..." -ForegroundColor Cyan
Copy-Item "dist\*" -Destination $portableDir -Recurse
Write-Host "  ✓ All executable files and dependencies" -ForegroundColor Green

# Copy resource directories
if (Test-Path "icons") {
    Copy-Item "icons" -Destination $portableDir -Recurse
    Write-Host "  ✓ Icons directory" -ForegroundColor Green
}

if (Test-Path "fonts") {
    Copy-Item "fonts" -Destination $portableDir -Recurse
    Write-Host "  ✓ Fonts directory" -ForegroundColor Green
}

Write-Host "`nCreating launcher and documentation..." -ForegroundColor White

# Create simple launcher batch file
@"
@echo off
chcp 65001 > nul
echo ========================================
echo   CLINICAL LABORATORY SOFTWARE
echo ========================================
echo.
echo Starting application...
echo.
ClinicalLabSoftware.exe
"@ | Out-File -FilePath "$portableDir\Run Clinical Software.bat" -Encoding ascii
Write-Host "  ✓ Run Clinical Software.bat" -ForegroundColor Green

# Create quick start guide
@"
QUICK START GUIDE
=================

1. Double-click 'Run Clinical Software.bat'
   OR
   Double-click 'ClinicalLabSoftware.exe'

2. First time login:
   Username: admin
   Password: admin

3. IMPORTANT: Change password immediately!

4. Your data is stored in:
   %APPDATA%\ClinicalLabSoftware\

NO INSTALLATION REQUIRED!
"@ | Out-File -FilePath "$portableDir\QUICK_START.txt" -Encoding utf8
Write-Host "  ✓ QUICK_START.txt" -ForegroundColor Green

# Display final information
$folderSize = [math]::Round((Get-ChildItem $portableDir -Recurse | Measure-Object -Property Length -Sum).Sum / 1MB, 2)
$exeSize = [math]::Round((Get-Item "dist\ClinicalLabSoftware.exe").Length / 1MB, 2)

Write-Host "`n" + "="*60 -ForegroundColor Green
Write-Host "🎉 PORTABLE PACKAGE CREATED SUCCESSFULLY!" -ForegroundColor Green
Write-Host "="*60 -ForegroundColor Green

Write-Host "`n📁 PACKAGE LOCATION: $portableDir\" -ForegroundColor Yellow
Write-Host "📊 Total size: $folderSize MB" -ForegroundColor Cyan
Write-Host "⚙️  Executable size: $exeSize MB" -ForegroundColor Cyan

Write-Host "`n📦 PACKAGE CONTENTS:" -ForegroundColor Green
Get-ChildItem $portableDir | ForEach-Object {
    if ($_.PSIsContainer) {
        Write-Host "  📁 $($_.Name)" -ForegroundColor Blue
    } else {
        Write-Host "  📄 $($_.Name)" -ForegroundColor White
    }
}

Write-Host "`n🚀 DEPLOYMENT INSTRUCTIONS:" -ForegroundColor Green
Write-Host "  1. Copy the ENTIRE '$portableDir' folder to USB" -ForegroundColor White
Write-Host "  2. On target computer, run 'Run Clinical Software.bat'" -ForegroundColor White
Write-Host "  3. Or run 'ClinicalLabSoftware.exe' directly" -ForegroundColor White
Write-Host "  4. Login with admin/admin" -ForegroundColor White

Write-Host "`n💡 IMPORTANT: Copy the ENTIRE folder, not just the .exe file!" -ForegroundColor Yellow
Write-Host "   This ensures all DLLs and dependencies are included." -ForegroundColor Yellow

Write-Host "`n✅ Portable package is ready for deployment!" -ForegroundColor Green