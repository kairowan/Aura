# 💠 Aura (基于字节跳动 Aura 二开版)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## ⚠️ 版权与开源声明 (Disclaimer)

本项目是基于 **[字节跳动 (Bytedance) 官方开源的 Aura 项目](https://github.com/bytedance/aura)** 进行的二次开发（Fork & Secondary Development）。
原项目遵循 **MIT 开源许可证**发布。

1. 我们严格遵守原有的 MIT 开源协议，保留了原项目目录下的 `LICENSE` 版权声明文件。
2. 我们对字节跳动 Aura 团队在 Super Agent Harness 领域的卓越开源贡献表示诚挚的感谢！
3. 本二开版本与字节跳动官方无任何商业从属关系，本项目产生的任何后果与原作者无关。

---

## 🚀 为什么要有这个二开版本？

原版的 Aura 强大的功能毋庸置疑，但它的部署方式偏向极客与开发者（需要懂命令行、配置环境变量、使用 Docker 等）。

**本项目的核心目标**是将这套极其强大的 Agent 引擎**彻底民用化、产品化**：

1. **💻 真正的桌面级客户端化**：打破原有浏览器的限制，提供独立的 Windows (`.exe`) 和 macOS (`.dmg`) 桌面原生客户端。
2. **⚡ 一行命令/一键极简安装**：彻底抛弃繁琐的 `make dev`、环境配置等极客操作，实现开箱即用的自动化部署体验。
3. **🔋 彻底的性能调优**：预置了强制进入生产模式的策略，禁用了占用 CPU 和几 GB 内存的开发态热更新，即使在普通的个人笔记本上也能如丝般顺滑运行。

---

## 📦 如何安装与使用

*(🚧 以下为规划中的安装方式，正在积极开发与打包中)*

### 方式一：全自动一行命令安装

**🍎 macOS / 🐧 Linux 用户终端一行执行：**
```bash
bash -c "$(curl -fsSL https://raw.githubusercontent.com/你的账号/你的仓库/main/install.sh)"
```

**🪟 Windows 用户 PowerShell 一行执行：**
```powershell
iwr -useb https://raw.githubusercontent.com/你的账号/你的仓库/main/install.ps1 | iex
```

### 方式二：下载独立桌面版客户端
您可以在本仓库右侧的 **[Releases](#)** 页面，直接下载最新版本的客户端安装包（即装即用）：
- `Aura-macOS.dmg`
- `Aura-Windows.exe`

---

## 🛠️ 项目使用与开发说明

对本二开项目的源码感兴趣的开发者，本项目依然保留了底层的强大扩展性（LangGraph、Skills、Tools）：

### 核心目录结构
- `/frontend`：基于 Next.js 的前端界面（即将支持 Electron/Tauri 打包封装）
- `/backend`：底层的 LangGraph 交互逻辑与 API Gateway
- `/skills/custom`：使用纯 Markdown 自然语言编写你专属的 AI 员工技能！

### 手动开发测试
为了防止手动启动出现错误，我们内置了极简化的启动脚本：
- **Mac 环境**：双击项目根目录下的 `start_optimized.command` 即可一键低占用启动服务。
- 修改大模型 API 依然在 `config.yaml` 或 `.env` 中进行。

---

## 🤝 鸣谢与支持
再次感谢字节跳动赋予 Aura 如此强悍的 AI 管线底座。欢迎各界开发者为将它打造成更完美的桌面端应用提交 PR 与建议！
