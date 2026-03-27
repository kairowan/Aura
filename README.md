# 💠 Aura (Based on Bytedance Aura)

[English](README.md) | [简体中文](README_zh.md) | [日本語](README_ja.md) | [Français](README_fr.md) | [Русский](README_ru.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## ⚠️ Disclaimer & Copyright

This project is a secondary development (fork) based on **[Bytedance's open-source Aura project](https://github.com/bytedance/deer-flow)**. 
The original project is released under the **MIT License**.

1. We strictly comply with the original MIT open-source agreement and have retained the original `LICENSE` file in the project directory.
2. We express our sincere gratitude to the Bytedance Aura team for their outstanding contributions to the Super Agent Harness ecosystem.
3. This secondary development version has no commercial affiliation with Bytedance, and any consequences arising from this project or its usage are completely unrelated to the original authors.

---

## 🚀 Why this Fork?

While the original Aura is incredibly powerful, its deployment process is heavily geared towards developers (requiring knowledge of command line, environment variables, Docker, etc.).

**The core goal of this project** is to completely productize this powerful Agent engine for everyday users:

1. **💻 Native Desktop Clients**: Breaking out of the browser by providing standalone `.exe` (Windows) and `.dmg` (macOS) applications.
2. **⚡ One-Line / One-Click Installation**: Abandoning complex `make dev` commands in favor of fully automated out-of-the-box deployment.
3. **🔋 Drastic Performance Tuning**: Automatically running in production mode, turning off heavy CPU/Memory development watchers, making it run smoothly even on standard laptops.

---

## 📦 Installation & Usage

*(🚧 These features are currently under active development)*

### Option 1: Automated One-Line Install

**🍎 macOS / 🐧 Linux Terminal:**
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/kairowan/Aura/main/install.sh)"
```

**🪟 Windows PowerShell:**
```powershell
iwr -useb https://raw.githubusercontent.com/kairowan/Aura/main/install.ps1 | iex
```

### Option 2: Build Desktop Client
For the native standalone desktop experience, you can build the Electron wrappers for macOS or Windows natively:

```bash
cd desktop
npm install
npm run dist:mac  # Generates Aura-macOS.dmg inside desktop/dist
# OR
npm run dist:win  # Generates Aura-Windows.exe inside desktop/dist
```

---

## 🛠️ Development

If you are a developer looking to contribute, the incredibly powerful underlying architecture of Aura (LangGraph, Skills, Tools) has been fully preserved.

- **Fast Track macOS Start**: Double-click `start_optimized.command` in the project root to start the production-grade tuned servers.

---

## 🤝 Acknowledgements
Thanks again to Bytedance for providing such a powerful AI pipeline foundation. PRs and suggestions are welcome!
