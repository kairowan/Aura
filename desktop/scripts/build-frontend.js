#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const repoRoot = path.resolve(__dirname, '..', '..');
const frontendDir = path.join(repoRoot, 'frontend');
const preparedEnvPath = path.join(__dirname, '..', 'vendor', 'build-resources', 'frontend.env');

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

function buildFrontend() {
  const env = { ...process.env };
  mergeEnvFile(env, preparedEnvPath);

  env.SKIP_ENV_VALIDATION = env.SKIP_ENV_VALIDATION || '1';
  env.BETTER_AUTH_SECRET = env.BETTER_AUTH_SECRET || 'aura_build_placeholder';
  env.BETTER_AUTH_URL = env.BETTER_AUTH_URL || 'http://localhost:3000';
  env.NEXT_PUBLIC_BACKEND_BASE_URL =
    env.NEXT_PUBLIC_BACKEND_BASE_URL || 'http://127.0.0.1:8001';
  env.NEXT_PUBLIC_LANGGRAPH_BASE_URL =
    env.NEXT_PUBLIC_LANGGRAPH_BASE_URL || 'http://127.0.0.1:2024';

  const pnpmCommand = process.platform === 'win32' ? 'pnpm.cmd' : 'pnpm';
  const result = spawnSync(pnpmCommand, ['build:desktop'], {
    cwd: frontendDir,
    env,
    stdio: 'inherit',
  });

  if (result.error) {
    throw result.error;
  }

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

buildFrontend();
