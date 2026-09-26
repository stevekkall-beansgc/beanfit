#!/bin/sh
# Compile check only: no signing, installation, model inference, or simulator boot.
set -eu
probe_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
probe_cache=$(mktemp -d "${TMPDIR:-/tmp}/beanfit-swift.XXXXXX")
trap 'rm -rf "$probe_cache"' EXIT
probe_sdk=$(xcrun --sdk iphonesimulator --show-sdk-path)
xcrun swiftc -typecheck -parse-as-library -swift-version 6 \
  -sdk "$probe_sdk" -target arm64-apple-ios26.0-simulator \
  -module-cache-path "$probe_cache" "$probe_dir/NativeTextProbe.swift"
probe_sdk=$(xcrun --sdk iphoneos --show-sdk-path)
xcrun swiftc -typecheck -parse-as-library -swift-version 6 \
  -sdk "$probe_sdk" -target arm64-apple-ios26.0 \
  -module-cache-path "$probe_cache" "$probe_dir/NativeTextProbe.swift"
echo 'PASS: iOS simulator and device SDK typechecks only; no device or inference execution'
