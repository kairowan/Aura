#!/usr/bin/env node

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const repoRoot = path.resolve(__dirname, '..', '..');
const outputDir = path.resolve(__dirname, '..', 'vendor', 'build-resources');

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
  return dirPath;
}

function emptyDir(dirPath) {
  fs.rmSync(dirPath, { recursive: true, force: true });
  fs.mkdirSync(dirPath, { recursive: true });
}

function copyFirstExisting(sourceCandidates, destinationPath, fallbackContent = '') {
  const source = sourceCandidates.find((candidate) => fs.existsSync(candidate));
  ensureDir(path.dirname(destinationPath));
  if (source) {
    fs.copyFileSync(source, destinationPath);
    return { source, destinationPath };
  }
  fs.writeFileSync(destinationPath, fallbackContent, 'utf8');
  return { source: null, destinationPath };
}

function parseEnvContent(content) {
  const values = {};
  content.split(/\r?\n/).forEach((line) => {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith('#')) {
      return;
    }

    const normalized = trimmed.startsWith('export ') ? trimmed.slice(7) : trimmed;
    const separatorIndex = normalized.indexOf('=');
    if (separatorIndex === -1) {
      return;
    }

    const key = normalized.slice(0, separatorIndex).trim();
    let value = normalized.slice(separatorIndex + 1).trim();
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }

    if (key) {
      values[key] = value;
    }
  });
  return values;
}

function ensureEnvDefaults(filePath, defaults) {
  const existingContent = fs.existsSync(filePath)
    ? fs.readFileSync(filePath, 'utf8')
    : '';
  const existingValues = parseEnvContent(existingContent);
  const missingEntries = Object.entries(defaults).filter(([key]) => {
    const value = existingValues[key];
    return typeof value !== 'string' || value.length === 0;
  });

  if (missingEntries.length === 0) {
    return;
  }

  const prefix = existingContent && !existingContent.endsWith('\n') ? '\n' : '';
  const appended = missingEntries
    .map(([key, value]) => `${key}=${JSON.stringify(value)}`)
    .join('\n');
  fs.writeFileSync(filePath, `${existingContent}${prefix}${appended}\n`, 'utf8');
}

function main() {
  emptyDir(outputDir);

  const frontendEnvResult = copyFirstExisting(
    [path.join(repoRoot, 'frontend', '.env'), path.join(repoRoot, 'frontend', '.env.example')],
    path.join(outputDir, 'frontend.env'),
    '',
  );

  ensureEnvDefaults(frontendEnvResult.destinationPath, {
    NEXT_PUBLIC_BACKEND_BASE_URL: 'http://127.0.0.1:8001',
    NEXT_PUBLIC_LANGGRAPH_BASE_URL: 'http://127.0.0.1:2024',
    BETTER_AUTH_SECRET: `aura_desktop_build_${crypto.randomBytes(24).toString('hex')}`,
    BETTER_AUTH_URL: 'http://127.0.0.1:3000',
  });

  const results = [
    copyFirstExisting(
      [path.join(repoRoot, 'config.yaml'), path.join(repoRoot, 'config.example.yaml')],
      path.join(outputDir, 'config.yaml'),
    ),
    copyFirstExisting(
      [path.join(repoRoot, 'extensions_config.json'), path.join(repoRoot, 'extensions_config.example.json')],
      path.join(outputDir, 'extensions_config.json'),
      JSON.stringify({ mcpServers: {}, skills: {} }, null, 2),
    ),
    copyFirstExisting(
      [path.join(repoRoot, '.env'), path.join(repoRoot, '.env.example')],
      path.join(outputDir, 'root.env'),
      '',
    ),
    frontendEnvResult,
  ];

  fs.writeFileSync(path.join(outputDir, 'manifest.json'), JSON.stringify(results, null, 2));
  console.log(`Prepared desktop build resources in ${outputDir}`);
}

main();
