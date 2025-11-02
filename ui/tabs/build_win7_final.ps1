# build_final_complete.ps1
Write-Host "=== BUILD WITH QT6 CHARTS FIX - WINDOWS 7 COMPATIBLE ===" -ForegroundColor Green

# Check Python
try {
    $pythonVersion = python --version
    Write-Host "Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "ERROR: Python not found!" -ForegroundColor Red
    exit 1
}

# Clean build directories
Write-Host "Cleaning build directories..." -ForegroundColor Yellow
Remove-Item -Recurse -Force dist, build -ErrorAction SilentlyContinue
Remove-Item *.spec -ErrorAction SilentlyContinue

Write-Host "Building with Qt6 Charts manual inclusion and Windows 7 compatibility..." -ForegroundColor Cyan

# Get Qt6 paths
$qt6Path = python -c "import PyQt6; import os; print(os.path.dirname(PyQt6.__file__))"
$qt6BinPath = Join-Path $qt6Path "Qt6\bin"

Write-Host "Qt6 Path: $qt6Path" -ForegroundColor Cyan
Write-Host "Qt6 Bin Path: $qt6BinPath" -ForegroundColor Cyan

# Build PyInstaller command as an array
$pyinstallerArgs = @(
    '--onedir',
    '--windowed',
    '--name', 'ClinicalLabSoftware',
    # Windows 7 compatibility flags (REMOVED --win-no-prefer-redirects)
    '--target-architecture', 'win32',
    '--disable-windowed-traceback',
    # Data files
    '--add-data', 'icons;icons',
    '--add-data', 'fonts;fonts',
    '--add-data', 'ui;ui',
    '--add-data', 'reports;reports',
    '--add-data', 'database.py;.',
    '--add-data', 'models.py;.',
    # Explicitly add Qt6 Charts DLLs and dependencies
    '--add-binary', "$qt6BinPath\Qt6Charts.dll;PyQt6\Qt6\bin",
    '--add-binary', "$qt6BinPath\Qt6ChartsQml.dll;PyQt6\Qt6\bin",
    '--add-binary', "$qt6BinPath\Qt6OpenGL.dll;PyQt6\Qt6\bin",
    # Core Qt6 modules
    '--collect-all', 'PyQt6',
    '--collect-all', 'PyQt6.QtCore',
    '--collect-all', 'PyQt6.QtGui',
    '--collect-all', 'PyQt6.QtWidgets',
    '--collect-all', 'PyQt6.QtCharts',
    # Application hidden imports
    '--hidden-import', 'database',
    '--hidden-import', 'models',
    '--hidden-import', 'ui.main_window',
    '--hidden-import', 'ui.login_dialog',
    '--hidden-import', 'ui.components.patient_form',
    '--hidden-import', 'ui.components.test_table',
    '--hidden-import', 'ui.tabs.dashboard',
    '--hidden-import', 'ui.tabs.patient',
    '--hidden-import', 'ui.tabs.order',
    '--hidden-import', 'ui.tabs.test',
    '--hidden-import', 'ui.tabs.result',
    '--hidden-import', 'ui.tabs.user',
    '--hidden-import', 'ui.tabs.report',
    '--hidden-import', 'reports.pdf_generator',
    '--hidden-import', 'reports.invoice_generator',
    # SQLAlchemy
    '--hidden-import', 'sqlalchemy',
    '--hidden-import', 'sqlalchemy.ext',
    '--hidden-import', 'sqlalchemy.ext.declarative',
    '--hidden-import', 'sqlalchemy.orm',
    '--hidden-import', 'sqlalchemy.engine',
    '--hidden-import', 'sqlalchemy.pool',
    '--hidden-import', 'sqlalchemy.event',
    '--hidden-import', 'sqlalchemy.util',
    '--hidden-import', 'sqlalchemy.sql',
    '--hidden-import', 'sqlalchemy.sql.expression',
    '--hidden-import', 'sqlalchemy.sql.functions',
    '--hidden-import', 'sqlalchemy.dialects',
    '--hidden-import', 'sqlalchemy.dialects.sqlite',
    '--hidden-import', 'sqlite3',
    # Other dependencies
    '--hidden-import', 'cryptography',
    '--hidden-import', 'cryptography.fernet',
    '--hidden-import', 'cryptography.hazmat',
    '--hidden-import', 'cryptography.hazmat.primitives',
    '--hidden-import', 'cryptography.hazmat.backends',
    '--hidden-import', 'qrcode',
    '--hidden-import', 'PIL',
    '--hidden-import', 'PIL.Image',
    '--hidden-import', 'PIL.ImageDraw',
    '--hidden-import', 'PIL.ImageFont',
    '--hidden-import', 'reportlab',
    '--hidden-import', 'reportlab.lib',
    '--hidden-import', 'reportlab.lib.pagesizes',
    '--hidden-import', 'reportlab.platypus',
    '--hidden-import', 'reportlab.pdfgen',
    '--hidden-import', 'reportlab.pdfbase',
    '--hidden-import', 'reportlab.pdfbase.ttfonts',
    '--hidden-import', 'reportlab.lib.styles',
    '--hidden-import', 'reportlab.lib.colors',
    '--hidden-import', 'reportlab.lib.units',
    '--hidden-import', 'reportlab.platypus.doctemplate',
    '--hidden-import', 'reportlab.platypus.frames',
    '--hidden-import', 'reportlab.platypus.flowables',
    '--hidden-import', 'reportlab.platypus.tables',
    '--hidden-import', 'reportlab.platypus.paragraph',
    '--hidden-import', 'reportlab.platypus.paraparser',
    '--hidden-import', 'reportlab.graphics',
    '--hidden-import', 'reportlab.graphics.shapes',
    '--hidden-import', 'reportlab.graphics.charts',
    '--hidden-import', 'reportlab.graphics.widgets',
    '--hidden-import', 'reportlab.graphics.barcode',
    'main.py'
)

# Execute PyInstaller
Write-Host "Running PyInstaller with Windows 7 compatibility..." -ForegroundColor Yellow
pyinstaller @pyinstallerArgs

# Check build result
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n=== BUILD SUCCESSFUL ===" -ForegroundColor Green
    Write-Host "Executable folder: .\dist\ClinicalLabSoftware" -ForegroundColor Yellow
    
    if (Test-Path "dist\ClinicalLabSoftware\ClinicalLabSoftware.exe") {
        $fileInfo = Get-Item "dist\ClinicalLabSoftware\ClinicalLabSoftware.exe"
        $fileSize = $fileInfo.Length / 1MB
        Write-Host "File size: $([math]::Round($fileSize, 2)) MB" -ForegroundColor Cyan
        Write-Host "Build completed with Qt6 Charts fix and Windows 7 compatibility!" -ForegroundColor Green
    }
} else {
    Write-Host "`n=== BUILD FAILED ===" -ForegroundColor Red
    exit 1
}