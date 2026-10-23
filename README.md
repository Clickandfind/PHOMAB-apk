# PHOMAB Android APK build

This repository package contains the PHOMAB V6 Kivy source and a GitHub Actions workflow to build a debug APK.

## Files
- `main.py` — PHOMAB V6 app source
- `buildozer.spec` — Buildozer Android configuration
- `.github/workflows/android.yml` — automated build workflow

## Build
1. Upload these files and folders to the root of the `Clickandfind/PHOMAB-apk` repository, keeping the paths shown above.
2. Open the repository's **Actions** tab.
3. Select **Build PHOMAB APK** and tap **Run workflow** (or push a commit to `main`).
4. When the run succeeds, open it and download the `PHOMAB-APK` artifact.

The current V6 source is a working local prototype. Listings, accounts, ride offers and chat history are stored on the device; sample driver offers are not real bookings. Online accounts, live listings, real dispatch/payments, and a connected generative AI service are not implemented in this source yet.
