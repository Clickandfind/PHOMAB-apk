[app]
title = PHOMAB
package.name = phomab
package.domain = org.clickandfind
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,ttf,json,txt
version = 6.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0

# Android settings
android.api = 33
android.minapi = 23
android.ndk = 25b
android.sdk_path = /usr/local/lib/android/sdk
android.ndk_path = /usr/local/lib/android/sdk/ndk/25.1.8937393
android.archs = arm64-v8a
android.accept_sdk_license = True
android.permissions = INTERNET

# The workflow installs the SDK/NDK at these fixed paths and provides a
# compatibility sdkmanager link for Buildozer versions expecting tools/bin.

[buildozer]
log_level = 2
warn_on_root = 1
