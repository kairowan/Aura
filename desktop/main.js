const { app, BrowserWindow, dialog, ipcMain } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const waitOn = require('wait-on');
const fs = require('fs');
const crypto = require('crypto');

let mainWindow;
let isShuttingDown = false;
const FRONTEND_PORT = 3000;
const GATEWAY_PORT = 8001;
const LANGGRAPH_PORT = 2024;
const SELECT_PROJECT_DIRECTORY_CHANNEL = 'aura:select-project-directory';

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

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

function mergeEnvFile(targetEnv, envPath) {
  if (!fs.existsSync(envPath)) {
    return;
  }

  const content = fs.readFileSync(envPath, 'utf8');
  content.split(/\r?\n/).forEach((rawLine) => {
    const trimmed = rawLine.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      return;
    }

    const line = trimmed.startsWith('export ') ? trimmed.slice(7) : trimmed;
    const separatorIndex = line.indexOf('=');
    if (separatorIndex === -1) {
      return;
    }

    const key = line.slice(0, separatorIndex).trim();
    if (!key) {
      return;
    }

    let value = line.slice(separatorIndex + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    targetEnv[key] = value;
  });
}

function createBaseEnv(extraEnv = {}, envFiles = []) {
  const env = { ...process.env };
  mergeEnvFile(env, path.join(rootDir, '.env'));
  envFiles.forEach((envFile) => mergeEnvFile(env, envFile));
  return { ...env, ...extraEnv };
}

function getRuntimeBaseDir() {
  return path.join(app.getPath('userData'), 'runtime');
}

function getAuraDataDir() {
  return path.join(getRuntimeBaseDir(), 'data');
}

function getRuntimeSkillsDir() {
  return path.join(getRuntimeBaseDir(), 'skills');
}

function getBackendRuntimeEnvDir() {
  return path.join(getRuntimeBaseDir(), 'backend-venv');
}

function getRuntimeBackendSourceDir() {
  return path.join(getRuntimeBaseDir(), 'backend-src');
}

function getRuntimeExtensionsConfigPath() {
  return path.join(getRuntimeBaseDir(), 'extensions_config.json');
}

function getRuntimeProviderConfigPath() {
  return path.join(getRuntimeBaseDir(), 'provider_config.json');
}

function getBundledOcrRuntimeDir() {
  if (process.platform !== 'darwin') {
    return null;
  }
  return isPackaged
    ? path.join(rootDir, 'ocr-runtime')
    : path.join(__dirname, 'vendor', 'tesseract-runtime');
}

function getBundledOcrEnv() {
  const runtimeDir = getBundledOcrRuntimeDir();
  if (!runtimeDir) {
    return {};
  }
  const binaryPath = path.join(runtimeDir, 'bin', 'tesseract');
  const tessdataDir = path.join(runtimeDir, 'share', 'tessdata');
  const libraryPath = path.join(runtimeDir, 'lib');

  if (!fs.existsSync(binaryPath) || !fs.existsSync(tessdataDir) || !fs.existsSync(libraryPath)) {
    return {};
  }

  return {
    AURA_TESSERACT_BINARY: binaryPath,
    AURA_TESSDATA_DIR: tessdataDir,
    AURA_TESSERACT_LIBRARY_PATH: libraryPath,
  };
}

function buildBackendPythonPath(backendDir) {
  const pythonPaths = [
    backendDir,
    path.join(backendDir, 'packages', 'harness'),
  ];
  const existingPythonPath = process.env.PYTHONPATH;
  if (existingPythonPath) {
    pythonPaths.push(existingPythonPath);
  }
  return pythonPaths.join(path.delimiter);
}

function getPackagedSeedDataDir() {
  return path.join(rootDir, 'seed-data');
}

function getSeedSyncManifestPath() {
  return path.join(getRuntimeBaseDir(), 'seed-sync.json');
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
  return dirPath;
}

function syncSeedPath(srcPath, destPath, { overwrite = false } = {}) {
  if (!fs.existsSync(srcPath)) {
    return;
  }

  const stat = fs.statSync(srcPath);
  if (stat.isDirectory()) {
    ensureDir(destPath);
    for (const entry of fs.readdirSync(srcPath, { withFileTypes: true })) {
      const nextSrcPath = path.join(srcPath, entry.name);
      const nextDestPath = path.join(destPath, entry.name);
      syncSeedPath(nextSrcPath, nextDestPath, { overwrite });
    }
    return;
  }

  ensureDir(path.dirname(destPath));
  if (!overwrite && fs.existsSync(destPath)) {
    return;
  }
  fs.copyFileSync(srcPath, destPath);
}

function syncBackendSource(srcPath, destPath) {
  if (!fs.existsSync(srcPath)) {
    return;
  }

  const stat = fs.statSync(srcPath);
  if (stat.isDirectory()) {
    const basename = path.basename(srcPath);
    if (
      basename === '.venv' ||
      basename === '.langgraph_api' ||
      basename === '__pycache__' ||
      basename === '.pytest_cache'
    ) {
      return;
    }

    ensureDir(destPath);
    for (const entry of fs.readdirSync(srcPath, { withFileTypes: true })) {
      syncBackendSource(
        path.join(srcPath, entry.name),
        path.join(destPath, entry.name),
      );
    }
    return;
  }

  if (srcPath.endsWith('.pyc') || srcPath.endsWith('.pyo')) {
    return;
  }

  ensureDir(path.dirname(destPath));
  fs.copyFileSync(srcPath, destPath);
}

function ensureRuntimeSeedData() {
  ensureDir(getRuntimeBaseDir());
  ensureDir(getAuraDataDir());
  const runtimeSkillsDir = ensureDir(getRuntimeSkillsDir());

  const runtimeAgentsDir = path.join(getAuraDataDir(), 'agents');
  const runtimeExtensionsConfigPath = getRuntimeExtensionsConfigPath();
  const seedManifest = readJsonFile(getSeedSyncManifestPath());
  const needsSync =
    !seedManifest ||
    seedManifest.appVersion !== app.getVersion() ||
    !fs.existsSync(runtimeAgentsDir) ||
    (fs.existsSync(runtimeAgentsDir) && fs.readdirSync(runtimeAgentsDir).length === 0) ||
    fs.readdirSync(runtimeSkillsDir).length === 0 ||
    !fs.existsSync(runtimeExtensionsConfigPath);

  if (!needsSync) {
    return;
  }

  const seedDataDir = getPackagedSeedDataDir();
  if (fs.existsSync(seedDataDir)) {
    syncSeedPath(path.join(seedDataDir, 'agents'), runtimeAgentsDir);
    syncSeedPath(path.join(seedDataDir, 'skills'), runtimeSkillsDir);
    syncSeedPath(path.join(seedDataDir, 'extensions_config.json'), runtimeExtensionsConfigPath);
  }

  if (!fs.existsSync(runtimeExtensionsConfigPath)) {
    fs.writeFileSync(
      runtimeExtensionsConfigPath,
      JSON.stringify({ mcpServers: {}, skills: {} }, null, 2),
      'utf8',
    );
  }

  fs.writeFileSync(
    getSeedSyncManifestPath(),
    JSON.stringify({ appVersion: app.getVersion() }, null, 2),
    'utf8',
  );
}

function hashFile(filePath) {
  const buffer = fs.readFileSync(filePath);
  return crypto.createHash('sha256').update(buffer).digest('hex');
}

function readJsonFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return null;
  }

  try {
    return JSON.parse(fs.readFileSync(filePath, 'utf8'));
  } catch {
    return null;
  }
}

function getBackendRuntimeManifestPath() {
  return path.join(getRuntimeBaseDir(), 'backend-runtime.json');
}

function readBackendRuntimeManifest() {
  return readJsonFile(getBackendRuntimeManifestPath());
}

function writeBackendRuntimeManifest(data) {
  ensureDir(getRuntimeBaseDir());
  fs.writeFileSync(getBackendRuntimeManifestPath(), JSON.stringify(data, null, 2));
}

function getBackendRuntimeInstallMode() {
  return 'non-editable-v1';
}

function findBackendSitePackagesDir(envDir) {
  const libDir = path.join(envDir, 'lib');
  if (!fs.existsSync(libDir)) {
    return null;
  }

  const candidates = fs.readdirSync(libDir, { withFileTypes: true })
    .filter((entry) => entry.isDirectory() && entry.name.startsWith('python'))
    .map((entry) => path.join(libDir, entry.name, 'site-packages'));

  return candidates.find((candidate) => fs.existsSync(candidate)) || null;
}

function hasEditableHarnessInstall(envDir) {
  const sitePackagesDir = findBackendSitePackagesDir(envDir);
  if (!sitePackagesDir) {
    return false;
  }

  const harnessPthPath = path.join(sitePackagesDir, '_aura_harness.pth');
  if (fs.existsSync(harnessPthPath)) {
    return true;
  }

  const distInfoDir = fs.readdirSync(sitePackagesDir, { withFileTypes: true })
    .find((entry) => entry.isDirectory() && entry.name.startsWith('aura_harness-') && entry.name.endsWith('.dist-info'));
  if (!distInfoDir) {
    return false;
  }

  const directUrlPath = path.join(sitePackagesDir, distInfoDir.name, 'direct_url.json');
  if (!fs.existsSync(directUrlPath)) {
    return false;
  }

  try {
    const directUrl = JSON.parse(fs.readFileSync(directUrlPath, 'utf8'));
    return Boolean(directUrl?.dir_info?.editable);
  } catch {
    return false;
  }
}

function getBackendRuntimeState({ envDir, runtimeBackendDir, lockHash }) {
  const pythonPath = getPackagedBackendPython();
  const manifest = readBackendRuntimeManifest();
  const envReady = fs.existsSync(pythonPath);
  const sourceReady = fs.existsSync(path.join(runtimeBackendDir, 'langgraph.json'));
  const editableHarnessInstall = envReady && hasEditableHarnessInstall(envDir);
  const manifestMatches =
    manifest &&
    manifest.lockHash === lockHash &&
    manifest.appVersion === app.getVersion() &&
    manifest.bundleRoot === rootDir &&
    manifest.installMode === getBackendRuntimeInstallMode();

  return {
    manifest,
    envReady,
    sourceReady,
    editableHarnessInstall,
    manifestMatches,
  };
}

function createAuraServiceEnv(extraEnv = {}) {
  const backendDir = path.join(rootDir, 'backend');
  const packagedEnv = isPackaged
    ? {
        AURA_EXTENSIONS_CONFIG_PATH: getRuntimeExtensionsConfigPath(),
        AURA_PROVIDER_CONFIG_PATH: getRuntimeProviderConfigPath(),
        AURA_SKILLS_PATH: getRuntimeSkillsDir(),
      }
    : {};
  return createBaseEnv(
    {
      AURA_HOME: ensureDir(getAuraDataDir()),
      AURA_CONFIG_PATH: path.join(rootDir, 'config.yaml'),
      AURA_DESKTOP_AUTOMATION_ENABLED: 'true',
      PYTHONDONTWRITEBYTECODE: '1',
      ...getBundledOcrEnv(),
      PYTHONPATH: buildBackendPythonPath(backendDir),
      CORS_ORIGINS: `http://localhost:${FRONTEND_PORT},http://127.0.0.1:${FRONTEND_PORT},http://localhost:3001,http://127.0.0.1:3001`,
      ...packagedEnv,
      ...extraEnv,
    },
  );
}

function getPackagedBackendPython() {
  const binDir = process.platform === 'win32' ? 'Scripts' : 'bin';
  const executable = process.platform === 'win32' ? 'python.exe' : 'python';
  return path.join(getBackendRuntimeEnvDir(), binDir, executable);
}

function getPackagedBackendExecutable(name) {
  const binDir = process.platform === 'win32' ? 'Scripts' : 'bin';
  const executable = process.platform === 'win32' ? `${name}.exe` : name;
  return path.join(getBackendRuntimeEnvDir(), binDir, executable);
}

function waitForServices(services, timeout = 45000) {
  return Promise.all(
    services.map(async (service) => {
      try {
        await waitOn({
          resources: [service.url],
          delay: 0,
          interval: 200,
          timeout,
          window: 200,
        });
      } catch (error) {
        const detail = error instanceof Error ? error.message : String(error);
        throw new Error(`${service.name} 启动失败: ${detail}`);
      }
    }),
  );
}

function resolveFrontendRuntime() {
  if (!isPackaged) {
    const frontendDir = path.join(rootDir, 'frontend');
    return {
      cwd: frontendDir,
      envFile: path.join(frontendDir, '.env'),
      serverScript: null,
    };
  }

  const runtimeRoot = path.join(rootDir, 'frontend-runtime');
  const serverCandidates = [
    path.join(runtimeRoot, 'server.js'),
    path.join(runtimeRoot, 'frontend', 'server.js'),
  ];
  const serverScript = serverCandidates.find((candidate) => fs.existsSync(candidate)) || serverCandidates[0];
  const cwd = path.dirname(serverScript);
  const envCandidates = [
    path.join(cwd, '.env'),
    path.join(runtimeRoot, '.env'),
  ];
  const envFile = envCandidates.find((candidate) => fs.existsSync(candidate)) || envCandidates[0];

  return { cwd, envFile, serverScript };
}

function showStartupError(title, detail = '') {
  const safeTitle = escapeHtml(title);
  const safeDetail = escapeHtml(detail || '请查看应用日志获取更多信息。');
  const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>${safeTitle}</title>
  <style>
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: linear-gradient(135deg, #fff7ed 0%, #ffffff 55%, #f8fafc 100%);
      color: #111827;
      display: flex;
      min-height: 100vh;
      align-items: center;
      justify-content: center;
      padding: 24px;
      box-sizing: border-box;
    }
    .panel {
      width: min(720px, 100%);
      background: rgba(255, 255, 255, 0.92);
      border: 1px solid rgba(251, 146, 60, 0.28);
      border-radius: 20px;
      box-shadow: 0 24px 80px rgba(15, 23, 42, 0.08);
      padding: 28px;
    }
    h1 {
      margin: 0 0 12px;
      font-size: 24px;
    }
    p {
      margin: 0 0 16px;
      color: #475569;
      line-height: 1.6;
    }
    pre {
      margin: 0;
      padding: 16px;
      background: #0f172a;
      color: #e2e8f0;
      border-radius: 14px;
      white-space: pre-wrap;
      word-break: break-word;
      font-size: 12px;
      line-height: 1.6;
    }
  </style>
</head>
<body>
  <div class="panel">
    <h1>${safeTitle}</h1>
    <p>Aura 未能完成启动。请根据下面的信息检查依赖、端口占用或打包产物是否完整。</p>
    <pre>${safeDetail}</pre>
  </div>
</body>
</html>`;

  if (mainWindow && !mainWindow.isDestroyed()) {
    mainWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(html)}`).catch(() => {});
  }

  if (detail) {
    dialog.showErrorBox(title, detail);
  }
}

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
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
    }
  });

  // Use absolute path for loading.html to avoid issues in packaged apps
  const loadingPath = path.join(__dirname, 'loading.html');
  console.log('Loading splash screen from:', loadingPath);
  mainWindow.loadFile(loadingPath).catch(err => {
    console.error('Failed to load loading.html:', err);
  });

  mainWindow.webContents.on('did-fail-load', (_event, code, description, validatedURL) => {
    if (validatedURL && validatedURL.startsWith(`http://127.0.0.1:${FRONTEND_PORT}`)) {
      showStartupError(
        'Aura 界面加载失败',
        `${description} (${code})\n${validatedURL}`,
      );
    }
  });

  mainWindow.on('closed', function () {
    mainWindow = null;
  });
}

function setupIPCHandlers() {
  ipcMain.removeHandler(SELECT_PROJECT_DIRECTORY_CHANNEL);
  ipcMain.handle(SELECT_PROJECT_DIRECTORY_CHANNEL, async () => {
    const ownerWindow = mainWindow || BrowserWindow.getFocusedWindow();
    const result = await dialog.showOpenDialog(ownerWindow ?? undefined, {
      title: '选择项目文件夹',
      properties: ['openDirectory'],
      buttonLabel: '绑定到当前线程',
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    const selectedPath = result.filePaths[0];
    return {
      path: selectedPath,
      name: path.basename(selectedPath),
    };
  });
}

function startSubProcess(name, cmd, args, cwd, options = {}) {
  console.log(`[STARTING] ${name} in ${cwd}...`);
  const isWindows = process.platform === 'win32';
  const { env = process.env, shell = true } = options;

  const child = spawn(cmd, args, { 
    cwd, 
    env,
    shell,
    detached: !isWindows 
  });

  child.stdout.on('data', (data) => forwardProcessOutput(name, data, false));
  child.stderr.on('data', (data) => forwardProcessOutput(name, data, true));
  
  child.on('close', (code) => {
    console.log(`[${name}] Exited with code ${code}`);
  });

  return child;
}

function forwardProcessOutput(name, data, isStderr = false) {
  const text = String(data);
  const lines = text.split(/\r?\n/).filter((line) => line.length > 0);
  for (const line of lines) {
    if (!isStderr) {
      console.log(`[${name}] ${line}`);
      continue;
    }

    if (
      line.includes(" - INFO - ") ||
      line.startsWith("INFO:") ||
      line.includes("[info")
    ) {
      console.log(`[${name}] ${line}`);
      continue;
    }

    if (
      line.includes(" - WARNING - ") ||
      line.startsWith("WARNING:") ||
      line.includes("[warning")
    ) {
      console.warn(`[${name} WARN] ${line}`);
      continue;
    }

    console.error(`[${name} ERROR] ${line}`);
  }
}

async function runInitCommand(name, cmd, args, cwd, options = {}) {
  console.log(`[INIT] Running ${name} setup...`);
  const { env = createAuraServiceEnv(), shell = true } = options;
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { cwd, shell, env });
    child.stdout.on('data', (d) => forwardProcessOutput(name, d, false));
    child.stderr.on('data', (d) => forwardProcessOutput(name, d, true));
    child.on('error', (error) => {
      reject(new Error(`${name} failed to start: ${error.message}`));
    });
    child.on('close', (code) => {
      if (code === 0) resolve();
      else reject(new Error(`${name} failed with code ${code}`));
    });
  });
}

async function ensurePackagedBackendRuntime(backendDir) {
  const envDir = getBackendRuntimeEnvDir();
  const runtimeBackendDir = getRuntimeBackendSourceDir();
  const lockfilePath = path.join(backendDir, 'uv.lock');
  const lockHash = hashFile(lockfilePath);
  const runtimeState = getBackendRuntimeState({ envDir, runtimeBackendDir, lockHash });
  const needsRefresh =
    !runtimeState.envReady ||
    !runtimeState.sourceReady ||
    !runtimeState.manifestMatches ||
    runtimeState.editableHarnessInstall;

  if (!needsRefresh) {
    return { envDir, runtimeBackendDir };
  }

  ensureDir(getRuntimeBaseDir());
  if (!runtimeState.sourceReady || !runtimeState.manifestMatches) {
    fs.rmSync(runtimeBackendDir, { recursive: true, force: true });
    syncBackendSource(backendDir, runtimeBackendDir);
  }
  if (runtimeState.editableHarnessInstall || !runtimeState.envReady || !runtimeState.manifestMatches) {
    fs.rmSync(envDir, { recursive: true, force: true });
  }

  updateLoadingStatus("正在准备 Python 运行环境...", "首次安装或版本更新时需要同步依赖");

  const runtimeEnv = createAuraServiceEnv({
    VIRTUAL_ENV: envDir,
  });

  try {
    if (!runtimeState.envReady || runtimeState.editableHarnessInstall || !runtimeState.manifestMatches) {
      await runInitCommand(
        "Backend Venv",
        "uv",
        ["venv", envDir],
        backendDir,
        { env: runtimeEnv, shell: false },
      );
    }

    await runInitCommand(
      "Backend Sync",
      "uv",
      ["sync", "--frozen", "--no-dev", "--active", "--no-editable"],
      backendDir,
      { env: runtimeEnv, shell: false },
    );
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    if (detail.includes('spawn uv ENOENT')) {
      throw new Error(
        "Aura 无法准备后端运行环境，因为当前机器上没有找到 uv。\n请先安装 uv，或使用包含预构建后端运行时的安装包。",
      );
    }
    throw error;
  }

  writeBackendRuntimeManifest({
    appVersion: app.getVersion(),
    lockHash,
    bundleRoot: rootDir,
    installMode: getBackendRuntimeInstallMode(),
  });

  return { envDir, runtimeBackendDir };
}

async function startAuraNativeBackend() {
  const startupStartedAt = Date.now();
  const bundledBackendDir = path.join(rootDir, 'backend');
  const frontendRuntime = resolveFrontendRuntime();
  let packagedBackendPython = null;
  let backendDir = bundledBackendDir;

  updateLoadingStatus("正在初始化 Aura...", "正在准备极光工作区");
  
  // ONLY configure env in development (Resources is read-only in production)
  if (!isPackaged) {
    configureFrontendEnv(rootDir);
  }
  
  // Optimization: Skip sync/install in production or if already present
  const venvExists = fs.existsSync(path.join(bundledBackendDir, '.venv'));
  const modulesExist = fs.existsSync(path.join(frontendRuntime.cwd, 'node_modules'));

  if (!isPackaged) {
    try {
      if (!venvExists) {
        updateLoadingStatus("正在配置本地环境...", "初次运行需要一些时间");
        await runInitCommand("Backend Sync", "uv", ["sync"], bundledBackendDir);
      }
      if (!modulesExist) {
        updateLoadingStatus("正在准备前端组件...", "正在部署本地资源");
        await runInitCommand("Frontend Install", "pnpm", ["install"], frontendRuntime.cwd);
      }
    } catch (err) {
      console.error("Initialization Warning:", err);
    }
  } else {
    ensureRuntimeSeedData();
    const runtimeInfo = await ensurePackagedBackendRuntime(bundledBackendDir);
    packagedBackendPython = getPackagedBackendPython();
    backendDir = runtimeInfo.runtimeBackendDir;
  }

  // Multi-plex spawn the 3 core Aura services natively
  updateLoadingStatus("正在加载核心动力...", "正在启动本地智能引擎");
  if (isPackaged) {
    const backendEnv = createAuraServiceEnv({
      VIRTUAL_ENV: getBackendRuntimeEnvDir(),
    });
    processes.gateway = startSubProcess(
      "Gateway",
      packagedBackendPython,
      ["-m", "uvicorn", "app.gateway.app:app", "--host", "127.0.0.1", "--port", String(GATEWAY_PORT)],
      backendDir,
      { env: backendEnv, shell: false }
    );

    processes.langgraph = startSubProcess(
      "LangGraph",
      getPackagedBackendExecutable("langgraph"),
      ["dev", "--no-browser", "--allow-blocking", "--no-reload", "--host", "127.0.0.1", "--port", String(LANGGRAPH_PORT)],
      backendDir,
      { env: backendEnv, shell: false }
    );
  } else {
    processes.gateway = startSubProcess(
      "Gateway", 
      "uv", 
      ["run", "uvicorn", "app.gateway.app:app", "--host", "127.0.0.1", "--port", String(GATEWAY_PORT)], 
      backendDir,
      { env: createAuraServiceEnv() }
    );

    processes.langgraph = startSubProcess(
      "LangGraph", 
      "uv", 
      ["run", "langgraph", "dev", "--no-browser", "--allow-blocking", "--no-reload", "--host", "127.0.0.1", "--port", String(LANGGRAPH_PORT)], 
      backendDir,
      { env: createAuraServiceEnv() }
    );
  }

  updateLoadingStatus("正在准备 Aura 界面...", "正在进入极光工作区");
  if (isPackaged) {
    if (!frontendRuntime.serverScript || !fs.existsSync(frontendRuntime.serverScript)) {
      throw new Error(
        `Packaged frontend runtime is missing. Expected server entry at:\n${frontendRuntime.serverScript}`,
      );
    }

    processes.frontend = startSubProcess(
      "Frontend",
      process.execPath,
      [frontendRuntime.serverScript],
      frontendRuntime.cwd,
      {
        shell: false,
        env: createBaseEnv(
          {
            ELECTRON_RUN_AS_NODE: "1",
            NODE_ENV: "production",
            HOSTNAME: "127.0.0.1",
            PORT: String(FRONTEND_PORT),
            BETTER_AUTH_URL: `http://127.0.0.1:${FRONTEND_PORT}`,
          },
          [frontendRuntime.envFile],
        ),
      },
    );
  } else {
    processes.frontend = startSubProcess(
      "Frontend", 
      "pnpm", 
      ["run", "dev"], 
      frontendRuntime.cwd,
      {
        env: createBaseEnv({}, [frontendRuntime.envFile]),
      },
    );
  }
  
  const criticalServices = [
    { name: "核心引擎", url: `http-get://127.0.0.1:${GATEWAY_PORT}/health` },
    { name: "工作区界面", url: `http-get://127.0.0.1:${FRONTEND_PORT}` },
  ];
  const backgroundServices = [
    { name: "LangGraph 服务", url: `tcp:127.0.0.1:${LANGGRAPH_PORT}` },
  ];

  console.log('Waiting for Aura local services to become ready...');
  updateLoadingStatus("正在等待界面加载...", "正在连接前端与核心引擎");

  try {
    await waitForServices(criticalServices, 45000);
    console.log(`[STARTUP] Critical services ready in ${Date.now() - startupStartedAt}ms`);
  } catch (err) {
    const message = err instanceof Error ? err.message : String(err);
    console.error('Aura service startup failed:', message);
    throw new Error(`桌面依赖服务未能按时启动。\n${message}`);
  }

  updateLoadingStatus("加载完成", "正在进入工作区...");

  if (mainWindow) {
    await mainWindow.loadURL(`http://127.0.0.1:${FRONTEND_PORT}/workspace`);
    console.log(`[STARTUP] Workspace loaded in ${Date.now() - startupStartedAt}ms`);
  }

  void waitForServices(backgroundServices, 45000)
    .then(() => {
      console.log(`[STARTUP] LangGraph background startup completed in ${Date.now() - startupStartedAt}ms`);
    })
    .catch((err) => {
      const detail = err instanceof Error ? err.message : String(err);
      console.error('LangGraph background startup failed:', detail);
    });
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
  setupIPCHandlers();
  createWindow();
  try {
    await startAuraNativeBackend();
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error);
    console.error('Aura failed to start:', detail);
    await killProcesses();
    showStartupError('Aura 启动失败', detail);
  }

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('before-quit', async (event) => {
  if (!isShuttingDown) {
    event.preventDefault();
    if (mainWindow) {
      const shutdownPath = path.join(__dirname, 'shutting_down.html');
      mainWindow.loadFile(shutdownPath).catch(() => {});
    }
    await killProcesses();
    setTimeout(() => { app.quit() }, 1000); // 1s grace period for subprocess exits
  }
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});
