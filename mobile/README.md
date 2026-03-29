# Aura Mobile Shell

This directory contains a Capacitor-based mobile shell for Android and iOS.

## What It Does

The mobile shell connects to an already deployed Aura web workspace. It is intentionally thin:

- Reuses the existing Aura web UI through a mobile webview
- Lets the user configure the Aura server URL on first launch
- Persists the server URL locally on the device
- Keeps a short history of recent Aura servers for quick switching

## What It Does Not Do

This shell does not run the local desktop runtime on the phone:

- No embedded Python backend
- No desktop automation or OCR host tooling
- No local Electron-only features

## Quick Start

1. Install dependencies:

```bash
cd mobile
npm install
```

2. Generate native projects:

```bash
npm run add:android
npm run add:ios
```

3. Sync the shell assets:

```bash
npm run sync
```

4. Open the native project:

```bash
npm run open:android
# or
npm run open:ios
```

## Runtime Assumption

On first launch, enter the URL of your deployed Aura web app. If you only enter the host root, the shell will default to `/workspace`.

## CI

This repository now includes [`mobile-shell.yml`](/Users/haonan/Desktop/python/aura/.github/workflows/mobile-shell.yml), which:

- Generates an Android project and uploads a debug APK
- Generates an iOS project and validates a simulator build without code signing
