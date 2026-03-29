#!/usr/bin/env node

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

function main() {
  emptyDir(outputDir);

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
    copyFirstExisting(
      [path.join(repoRoot, 'frontend', '.env'), path.join(repoRoot, 'frontend', '.env.example')],
      path.join(outputDir, 'frontend.env'),
      'NEXT_PUBLIC_BACKEND_BASE_URL="http://127.0.0.1:8001"\nNEXT_PUBLIC_LANGGRAPH_BASE_URL="http://127.0.0.1:2024"\nBETTER_AUTH_SECRET="aura_build_placeholder"\nBETTER_AUTH_URL="http://localhost:3000"\n',
    ),
  ];

  fs.writeFileSync(path.join(outputDir, 'manifest.json'), JSON.stringify(results, null, 2));
  console.log(`Prepared desktop build resources in ${outputDir}`);
}

main();
