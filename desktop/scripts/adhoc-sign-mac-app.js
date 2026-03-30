#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

function hasExplicitSigningIdentity() {
  return Boolean(
    process.env.CSC_LINK ||
      process.env.CSC_NAME ||
      process.env.APPLE_CERTIFICATE_SIGNING_IDENTITY ||
      process.env.APPLE_IDENTITY,
  );
}

module.exports = async function afterPack(context) {
  if (context.electronPlatformName !== 'darwin' || hasExplicitSigningIdentity()) {
    return;
  }

  const productFilename = context.packager.appInfo.productFilename;
  const appPath = path.join(context.appOutDir, `${productFilename}.app`);

  if (!fs.existsSync(appPath)) {
    throw new Error(`Unable to locate packaged macOS app for ad-hoc signing: ${appPath}`);
  }

  console.log(`Applying ad-hoc bundle signature to ${appPath}`);
  execFileSync(
    'codesign',
    ['--force', '--deep', '--sign', '-', '--timestamp=none', appPath],
    { stdio: 'inherit' },
  );

  execFileSync(
    'codesign',
    ['--verify', '--deep', '--strict', '--verbose=2', appPath],
    { stdio: 'inherit' },
  );
};
