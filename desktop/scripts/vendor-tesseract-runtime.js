#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const desktopDir = path.resolve(__dirname, '..');
const outputDir = path.join(desktopDir, 'vendor', 'tesseract-runtime');
const cacheDir = path.join(desktopDir, 'vendor-cache', 'tesseract-traineddata');
const systemPrefixes = ['/usr/lib/', '/System/Library/'];
const homebrewPrefixes = ['/opt/homebrew/', '/usr/local/'];
const trainedDataFiles = {
  'eng.traineddata': { url: null, required: true },
  'osd.traineddata': { url: null, required: true },
  'snum.traineddata': { url: null, required: true },
  'chi_sim.traineddata': {
    url: 'https://raw.githubusercontent.com/tesseract-ocr/tessdata_best/main/chi_sim.traineddata',
    required: false,
  },
};

function run(command, args) {
  return execFileSync(command, args, { encoding: 'utf8' }).trim();
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
  return dirPath;
}

function emptyDir(dirPath) {
  fs.rmSync(dirPath, { recursive: true, force: true });
  fs.mkdirSync(dirPath, { recursive: true });
}

function hasPreparedRuntime(dirPath) {
  if (!fs.existsSync(dirPath)) {
    return false;
  }

  const binaryPath = path.join(dirPath, 'bin', 'tesseract');
  const tessdataDir = path.join(dirPath, 'share', 'tessdata');
  const manifestPath = path.join(dirPath, 'manifest.json');

  if (!fs.existsSync(binaryPath) || !fs.existsSync(tessdataDir) || !fs.existsSync(manifestPath)) {
    return false;
  }

  return Object.entries(trainedDataFiles)
    .filter(([, descriptor]) => descriptor.required)
    .every(([fileName]) =>
    fs.existsSync(path.join(tessdataDir, fileName)),
  );
}

function downloadFile(url, destination) {
  ensureDir(path.dirname(destination));
  execFileSync('curl', ['-fsSL', url, '-o', destination], { stdio: 'inherit' });
  return destination;
}

function resolveSourceBinary() {
  if (process.env.AURA_TESSERACT_SOURCE) {
    return fs.realpathSync(process.env.AURA_TESSERACT_SOURCE);
  }
  return fs.realpathSync(run('which', ['tesseract']));
}

function shouldBundle(depPath) {
  return homebrewPrefixes.some((prefix) => depPath.startsWith(prefix)) && !systemPrefixes.some((prefix) => depPath.startsWith(prefix));
}

function parseOtoolDependencies(filePath) {
  const output = run('otool', ['-L', filePath]);
  return output
    .split('\n')
    .slice(1)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => line.split(' (')[0]);
}

function findDependency(depPath, parentPath) {
  if (depPath.startsWith('@loader_path/')) {
    const candidate = path.resolve(path.dirname(parentPath), depPath.slice('@loader_path/'.length));
    if (fs.existsSync(candidate)) {
      return fs.realpathSync(candidate);
    }
  }

  if (depPath.startsWith('@rpath/')) {
    const fileName = path.basename(depPath);
    const parentDir = path.dirname(parentPath);
    const directCandidate = path.join(parentDir, fileName);
    if (fs.existsSync(directCandidate)) {
      return fs.realpathSync(directCandidate);
    }

    for (const prefix of ['/opt/homebrew', '/usr/local']) {
      const found = run('find', [prefix, '-path', '*/lib/*', '-name', fileName, '-print', '-quit']);
      if (found) {
        return fs.realpathSync(found);
      }
    }
    return null;
  }

  if (path.isAbsolute(depPath) && fs.existsSync(depPath)) {
    return fs.realpathSync(depPath);
  }

  return null;
}

function collectLibraryDirectories(binaryPath) {
  const queue = [binaryPath];
  const visitedFiles = new Set();
  const libraryDirs = new Set();

  while (queue.length > 0) {
    const current = queue.pop();
    if (!current || visitedFiles.has(current)) {
      continue;
    }
    visitedFiles.add(current);

    for (const dep of parseOtoolDependencies(current)) {
      const resolved = findDependency(dep, current);
      if (!resolved || !shouldBundle(resolved)) {
        continue;
      }
      libraryDirs.add(path.dirname(resolved));
      if (!visitedFiles.has(resolved)) {
        queue.push(resolved);
      }
    }
  }

  return [...libraryDirs];
}

function copyLibs(libraryDirs, destinationDir) {
  const copied = new Set();
  for (const dir of libraryDirs) {
    for (const entry of fs.readdirSync(dir)) {
      if (!entry.endsWith('.dylib')) {
        continue;
      }
      const sourcePath = path.join(dir, entry);
      const destPath = path.join(destinationDir, entry);
      if (copied.has(destPath)) {
        continue;
      }
      fs.copyFileSync(sourcePath, destPath);
      copied.add(destPath);
    }
  }
  return [...copied].map((filePath) => path.basename(filePath)).sort();
}

function resolveTessdataDir(binaryPath) {
  const sourceRoot = path.resolve(path.dirname(binaryPath), '..');
  const bundledDir = path.join(sourceRoot, 'share', 'tessdata');
  if (fs.existsSync(bundledDir)) {
    return bundledDir;
  }

  const prefix = run('brew', ['--prefix', 'tesseract']);
  const brewDir = path.join(prefix, 'share', 'tessdata');
  if (fs.existsSync(brewDir)) {
    return brewDir;
  }

  throw new Error('Unable to locate tessdata for tesseract.');
}

function ensureRequiredTrainedData(sourceTessdataDir, destinationTessdataDir) {
  ensureDir(cacheDir);
  const installed = [];

  for (const [fileName, descriptor] of Object.entries(trainedDataFiles)) {
    const sourcePath = path.join(sourceTessdataDir, fileName);
    const cachePath = path.join(cacheDir, fileName);
    const destinationPath = path.join(destinationTessdataDir, fileName);

    if (fs.existsSync(sourcePath)) {
      fs.copyFileSync(sourcePath, destinationPath);
      installed.push(fileName);
      continue;
    }

    if (!fs.existsSync(cachePath)) {
      if (!descriptor.url) {
        throw new Error(`Missing required traineddata file: ${fileName}`);
      }
      try {
        downloadFile(descriptor.url, cachePath);
      } catch (error) {
        if (descriptor.required) {
          throw error;
        }
        console.warn(`Skipping optional traineddata ${fileName}: ${error.message}`);
        continue;
      }
    }

    fs.copyFileSync(cachePath, destinationPath);
    installed.push(fileName);
  }

  return installed.sort();
}

function main() {
  if (process.platform !== 'darwin') {
    emptyDir(outputDir);
    console.log('Skipping tesseract runtime vendoring on non-macOS platform.');
    return;
  }

  if (process.env.AURA_FORCE_REBUILD_OCR_RUNTIME !== '1' && hasPreparedRuntime(outputDir)) {
    console.log(`Reusing existing tesseract runtime from ${outputDir}`);
    return;
  }

  const sourceBinary = resolveSourceBinary();
  const sourceTessdata = resolveTessdataDir(sourceBinary);
  const libraryDirs = collectLibraryDirectories(sourceBinary);

  emptyDir(outputDir);
  const binDir = ensureDir(path.join(outputDir, 'bin'));
  const libDir = ensureDir(path.join(outputDir, 'lib'));
  const shareDir = ensureDir(path.join(outputDir, 'share'));

  const binaryDestination = path.join(binDir, 'tesseract');
  fs.copyFileSync(sourceBinary, binaryDestination);
  fs.chmodSync(binaryDestination, 0o755);

  const bundledLibraries = copyLibs(libraryDirs, libDir);
  const destinationTessdataDir = path.join(shareDir, 'tessdata');
  fs.cpSync(sourceTessdata, destinationTessdataDir, { recursive: true });
  const bundledLanguages = ensureRequiredTrainedData(sourceTessdata, destinationTessdataDir);

  const manifest = {
    generatedAt: new Date().toISOString(),
    sourceBinary,
    sourceTessdata,
    libraries: bundledLibraries,
    traineddata: bundledLanguages,
  };
  fs.writeFileSync(path.join(outputDir, 'manifest.json'), JSON.stringify(manifest, null, 2));

  console.log(`Bundled tesseract runtime to ${outputDir}`);
  console.log(`Libraries: ${bundledLibraries.length}`);
}

main();
