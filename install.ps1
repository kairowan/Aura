# Aura Native Auto-Installer for Windows PowerShell
$ErrorActionPreference = "Stop"

$REPO_URL = "https://github.com/YOUR_ACCOUNT/aura.git"
$INSTALL_DIR = "$HOME\Aura"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " 💠 Aura Native Installer (Windows)" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "⚙️  Checking System Dependencies (Requires administrator privileges for some packages)..."
if (-not (Get-Command "winget" -ErrorAction SilentlyContinue)) {
    Write-Host "⚠️  Warning: winget is not installed. You may need to manually install Node, Python, and Git." -ForegroundColor Yellow
} else {
    if (-not (Get-Command "git" -ErrorAction SilentlyContinue)) {
        Write-Host "📦 Installing git..."
        winget install --id Git.Git -e --source winget
    }
    
    if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
        Write-Host "🐍 Installing Python..."
        winget install --id Python.Python.3.12 -e --source winget
    }
    
    if (-not (Get-Command "node" -ErrorAction SilentlyContinue)) {
        Write-Host "🟢 Installing Node.js..."
        winget install --id OpenJS.NodeJS -e --source winget
    }
}

if (-not (Get-Command "uv" -ErrorAction SilentlyContinue)) {
    Write-Host "⚡ Installing uv (Python package manager)..."
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
}

# 2. Clone repository
if (Test-Path $INSTALL_DIR) {
    Write-Host "⚠️  Directory $INSTALL_DIR already exists. Updating..." -ForegroundColor Yellow
    Set-Location $INSTALL_DIR
    git pull origin main
} else {
    Write-Host "📥 Cloning Aura into $INSTALL_DIR..."
    git clone $REPO_URL $INSTALL_DIR
    Set-Location $INSTALL_DIR
}

# 3. Setup configurations
Write-Host "⚙️  Setting up Aura configuration files..."
if (-not (Test-Path "config.yaml")) {
    Copy-Item "config.example.yaml" "config.yaml"
}
if (-not (Test-Path ".env")) {
    New-Item -ItemType File -Name ".env" -Force | Out-Null
}
if (-not (Test-Path "frontend\.env")) {
    if (-not (Test-Path "frontend")) { New-Item -ItemType Directory -Name "frontend" -Force | Out-Null }
    Set-Content -Path "frontend\.env" -Value 'NEXT_PUBLIC_BACKEND_BASE_URL="http://127.0.0.1:8001"'
    Add-Content -Path "frontend\.env" -Value 'NEXT_PUBLIC_LANGGRAPH_BASE_URL="http://127.0.0.1:2024"'
}

# 4. Create Desktop Shortcut for Windows
Write-Host "🪟 Creating Windows Desktop Shortcut..."
$WshShell = New-Object -comObject WScript.Shell
$DesktopPath = [Environment]::GetFolderPath("Desktop")
$Shortcut = $WshShell.CreateShortcut("$DesktopPath\Aura Client.lnk")
$Shortcut.TargetPath = "cmd.exe"
$Shortcut.Arguments = "/c cd /d `"$INSTALL_DIR\desktop`" && npm start"
$Shortcut.WorkingDirectory = "$INSTALL_DIR\desktop"
$Shortcut.IconLocation = "cmd.exe"
$Shortcut.Description = "Start Native Aura Client"
$Shortcut.Save()

Write-Host "✓ Shortcut created at: $DesktopPath\Aura Client.lnk" -ForegroundColor Green

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " 🎉 Native Installation Complete!" -ForegroundColor Cyan
Write-Host " 您现在可以双击桌面上的 'Aura Client' 直接原生启动客户端了！"
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
