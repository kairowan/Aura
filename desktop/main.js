const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const waitOn = require('wait-on');
const fs = require('fs');

let mainWindow;
let isShuttingDown = false;

// Store process references so we can kill them later
let processes = {
  frontend: null,
  gateway: null,
  langgraph: null
};

// Fix PATH for packaged apps on macOS to ensure common binary locations are included
if (process.platform === 'darwin') {
  const envPath = process.env.PATH || '';
  const home = process.env.HOME || '';
  const standardPaths = [
    '/usr/local/bin',
    '/usr/bin',
    '/bin',
    '/usr/sbin',
    '/sbin',
    '/opt/homebrew/bin',
    '/opt/homebrew/sbin',
    path.join(home, '.local', 'bin'),
    path.join(home, '.pnpm-global', 'bin'),
    path.join(home, 'Library', 'Application Support', 'pnpm')
  ].join(':');
  process.env.PATH = `${envPath}:${standardPaths}`;
}

// Function to send status updates to the loading screen
function updateLoadingStatus(message, subMessage = '') {
  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.webContents.executeJavaScript(`
      if (document.querySelector('.status')) {
        document.querySelector('.status').innerText = ${JSON.stringify(message)};
      }
      if (document.querySelector('.sub-status')) {
        document.querySelector('.sub-status').innerText = ${JSON.stringify(subMessage)};
      }
    `).catch(() => {});
  }
}

// Get the root directory correctly whether in development or packaged
const isPackaged = app.isPackaged;
const rootDir = isPackaged 
  ? process.resourcesPath 
  : path.join(__dirname, '..');

console.log('App is packaged:', isPackaged);
console.log('Root Directory:', rootDir);

// Ensure frontend env is configured to bypass NGINX via 127.0.0.1
function configureFrontendEnv(rootDir) {
  const envPath = path.join(rootDir, 'frontend', '.env');
  let envContent = '';
  if (fs.existsSync(envPath)) {
    envContent = fs.readFileSync(envPath, 'utf8');
  }
  
  const gatewayMatch = envContent.includes('NEXT_PUBLIC_BACKEND_BASE_URL');
  const langgraphMatch = envContent.includes('NEXT_PUBLIC_LANGGRAPH_BASE_URL');
  
  let needsWrite = false;
  if (!gatewayMatch) {
    envContent += '\nNEXT_PUBLIC_BACKEND_BASE_URL="http://127.0.0.1:8001"';
    needsWrite = true;
  }
  if (!langgraphMatch) {
    envContent += '\nNEXT_PUBLIC_LANGGRAPH_BASE_URL="http://127.0.0.1:2024"';
    needsWrite = true;
  }
  
  if (needsWrite) {
    if (!fs.existsSync(path.join(rootDir, 'frontend'))) {
      fs.mkdirSync(path.join(rootDir, 'frontend'));
    }
    fs.writeFileSync(envPath, envContent);
    console.log('Automatically configured frontend/.env to bypass Docker Nginx proxy.');
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1280,
    height: 800,
    title: "Aura",
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Use absolute path for loading.html to avoid issues in packaged apps
  const loadingPath = path.join(__dirname, 'loading.html');
  console.log('Loading splash screen from:', loadingPath);
  mainWindow.loadFile(loadingPath).catch(err => {
    console.error('Failed to load loading.html:', err);
  });

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

function startSubProcess(name, cmd, args, cwd) {
  console.log(`[STARTING] ${name} in ${cwd}...`);
  const backendDir = path.join(rootDir, 'backend');
  const isWindows = process.platform === 'win32';
  
  // Prepare environment variables
  const env = { 
    ...process.env,
    AURA_HOME: rootDir,
    AURA_CONFIG_PATH: path.join(rootDir, 'config.yaml'),
    PYTHONPATH: backendDir,
    CORS_ORIGINS: "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
  };

  // Merge variables from root .env if it exists
  const rootEnvPath = path.join(rootDir, '.env');
  if (fs.existsSync(rootEnvPath)) {
    try {
      const content = fs.readFileSync(rootEnvPath, 'utf8');
      content.split('\n').forEach(line => {
        const [key, ...valueParts] = line.split('=');
        if (key && valueParts.length > 0) {
          env[key.trim()] = valueParts.join('=').trim();
        }
      });
    } catch (e) {
      console.error(`Failed to parse root .env:`, e);
    }
  }

  const child = spawn(cmd, args, { 
    cwd, 
    env,
    shell: true,
    detached: !isWindows 
  });

  child.stdout.on('data', (data) => console.log(`[${name}] ${data}`));
  child.stderr.on('data', (data) => console.error(`[${name} ERROR] ${data}`));
  
  child.on('close', (code) => {
    console.log(`[${name}] Exited with code ${code}`);
  });

  return child;
}

async function runInitCommand(name, cmd, args, cwd) {
  console.log(`[INIT] Running ${name} setup...`);
  const isWindows = process.platform === 'win32';
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { cwd, shell: true });
    child.stdout.on('data', (d) => console.log(`[${name}] ${d}`));
    child.stderr.on('data', (d) => console.error(`[${name} ERR] ${d}`));
    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${name} failed with code ${code}`));
    });
  });
}

async function startAuraNativeBackend() {
  const backendDir = path.join(rootDir, 'backend');
  const frontendDir = path.join(rootDir, 'frontend');

  updateLoadingStatus("正在初始化 Aura...", "正在准备极光工作区");
  
  // ONLY configure env in development (Resources is read-only in production)
  if (!isPackaged) {
    configureFrontendEnv(rootDir);
  }
  
  // Optimization: Skip sync/install in production or if already present
  const venvExists = fs.existsSync(path.join(backendDir, '.venv'));
  const modulesExist = fs.existsSync(path.join(frontendDir, 'node_modules'));

  if (!isPackaged) {
    try {
      if (!venvExists) {
        updateLoadingStatus("正在配置本地环境...", "初次运行需要一些时间");
        await runInitCommand("Backend Sync", "uv", ["sync"], backendDir);
      }
      if (!modulesExist) {
        updateLoadingStatus("正在准备前端组件...", "正在部署本地资源");
        await runInitCommand("Frontend Install", "pnpm", ["install"], frontendDir);
      }
    } catch (err) {
      console.error("Initialization Warning:", err);
    }
  }

  // Multi-plex spawn the 3 core Aura services natively
  updateLoadingStatus("正在加载核心动力...", "正在启动本地智能引擎");
  processes.gateway = startSubProcess(
    "Gateway", 
    "uv", 
    ["run", "uvicorn", "app.gateway.app:app", "--host", "127.0.0.1", "--port", "8001"], 
    backendDir
  );

  processes.langgraph = startSubProcess(
    "LangGraph", 
    "uv", 
    ["run", "langgraph", "dev", "--no-browser", "--allow-blocking", "--host", "127.0.0.1", "--port", "2024"], 
    backendDir
  );

  processes.frontend = startSubProcess(
    "Frontend", 
    "pnpm", 
    ["run", "dev"], 
    frontendDir
  );

  // Improved service waiting logic with specific status reporting
  const services = [
    { name: "智能大脑 (Port 8001)", url: "http-get://127.0.0.1:8001/health" },
    { name: "逻辑引擎 (Port 2024)", url: "http-get://127.0.0.1:2024" },
    { name: "工作区界面 (Port 3000)", url: "http-get://127.0.0.1:3000" }
  ];

  console.log('Waiting for Aura local services to become ready...');
  
  for (const service of services) {
    updateLoadingStatus(`正在加载${service.name}...`, "这通常需要几秒钟");
    try {
      await waitOn({
        resources: [service.url],
        delay: 500,
        interval: 1000,
        timeout: 60000, // 1 minute per service
        window: 500
      });
    } catch (err) {
      console.error(`Service ${service.name} failed to start:`, err);
      updateLoadingStatus(`${service.name} 启动异常`, "请检查系统端口占用情况");
      // Continue and try others, or show error?
    }
  }
  
  updateLoadingStatus("加载完成", "正在进入工作区...");
  
  if (mainWindow) {
    // Final wait check for frontend to be fully ready before navigation
    setTimeout(() => {
      mainWindow.loadURL('http://127.0.0.1:3000/workspace');
    }, 1000);
  }
}

async function killProcesses() {
  if (isShuttingDown) return;
  isShuttingDown = true;
  
  console.log('Shutting down Aura native background processes...');
  Object.keys(processes).forEach((key) => {
    const p = processes[key];
    if (p && !p.killed) {
      console.log(`Killing ${key}...`);
      if (process.platform === 'win32') {
        spawn("taskkill", ["/pid", p.pid, '/f', '/t']);
      } else {
        try {
          process.kill(-p.pid, 'SIGINT'); // Kill process group on map/linux
        } catch (e) {
          p.kill('SIGINT');
        }
      }
    }
  });
}

app.whenReady().then(async () => {
  createWindow();
  await startAuraNativeBackend();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('before-quit', async (event) => {
  if (!isShuttingDown) {
    event.preventDefault();
    if (mainWindow) mainWindow.loadFile('shutting_down.html').catch(() => {});
    await killProcesses();
    setTimeout(() => { app.quit() }, 1000); // 1s grace period for subprocess exits
  }
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});
