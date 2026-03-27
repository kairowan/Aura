#!/usr/bin/env bash
# Aura Native Auto-Installer for macOS / Linux
set -e

REPO_URL=${REPO_URL:-"https://github.com/YOUR_ACCOUNT/aura.git"}
INSTALL_DIR=${INSTALL_DIR:-"$HOME/Aura"}

echo "=========================================="
echo " 💠 Aura Native Installer (macOS/Linux)"
echo "=========================================="
echo ""

# 1. Check and Auto-Install Dependencies
echo "⚙️  Checking System Dependencies..."

if [[ "$OSTYPE" == "darwin"* ]]; then
    if ! command -v brew &> /dev/null; then
        echo "🍺 Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    if ! command -v git &> /dev/null; then
        echo "📦 Installing git..."
        brew install git
    fi
    
    if ! command -v python3 &> /dev/null; then
        echo "🐍 Installing Python..."
        brew install python
    fi
    
    if ! command -v node &> /dev/null; then
        echo "🟢 Installing Node.js..."
        brew install node
    fi
    
    if ! command -v pnpm &> /dev/null; then
        echo "📦 Installing pnpm..."
        brew install pnpm
    fi
else
    # Linux (Debian/Ubuntu fallback)
    if ! command -v git &> /dev/null || ! command -v python3 &> /dev/null || ! command -v node &> /dev/null; then
        echo "📦 Installing system packages (may require sudo)..."
        sudo apt-get update
        sudo apt-get install -y git python3 python3-pip python3-venv nodejs npm
        sudo npm install -g pnpm
    fi
fi

if ! command -v uv &> /dev/null; then
    echo "⚡ Installing uv (Python package manager)..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
    export PATH="$HOME/.local/bin:$PATH"
fi

# 2. Clone repository
if [ -d "$INSTALL_DIR" ]; then
    echo "⚠️  Directory $INSTALL_DIR already exists. Updating..."
    cd "$INSTALL_DIR"
    git pull origin main
else
    echo "📥 Cloning Aura into $INSTALL_DIR..."
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 3. Setup configurations
echo "⚙️  Setting up Aura configuration files..."
if [ ! -f "config.yaml" ]; then
    cp config.example.yaml config.yaml
fi
if [ ! -f ".env" ]; then
    touch .env
fi
if [ ! -f "frontend/.env" ]; then
    echo 'NEXT_PUBLIC_BACKEND_BASE_URL="http://localhost:8001"' > frontend/.env
    echo 'NEXT_PUBLIC_LANGGRAPH_BASE_URL="http://localhost:2024"' >> frontend/.env
fi

# 4. Create Desktop Shortcut for macOS
if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "🍎 Creating macOS Desktop Shortcut..."
    SHORTCUT_PATH="$HOME/Desktop/Aura Client.command"
    cat > "$SHORTCUT_PATH" << EOF
#!/usr/bin/env bash
cd "$INSTALL_DIR/desktop"
npm start
EOF
    chmod +x "$SHORTCUT_PATH"
fi

echo ""
echo "=========================================="
echo " 🎉 Native Installation Complete!"
echo " 您现在可以双击桌面上的 'Aura Client.command' 直接原生启动客户端了！"
echo "=========================================="
