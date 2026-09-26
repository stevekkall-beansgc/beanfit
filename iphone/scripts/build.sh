#!/bin/bash
set -euo pipefail
# The source checkout and model files are acquired separately and hash-pinned.
: "${BF_LLAMA_SOURCE:?Set BF_LLAMA_SOURCE to the pinned llama.cpp checkout}"
: "${BF_OUTPUT:?Set BF_OUTPUT to an output directory outside the repository}"
platform="${1:-iphonesimulator}"
case "$platform" in iphoneos|iphonesimulator) ;; *) exit 2;; esac
root="$(cd "$(dirname "$0")/.." && pwd)"
revision=2145525a4081d66ff1a87cf43ef809f95a85ac0c
if [ -d "$BF_LLAMA_SOURCE/.git" ]; then
  test "$(git -C "$BF_LLAMA_SOURCE" rev-parse HEAD)" = "$revision"
fi
native="$BF_OUTPUT/native-$platform"
"${CMAKE:-cmake}" -S "$BF_LLAMA_SOURCE" -B "$native" \
  -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT="$platform" \
  -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=26.0 \
  -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=OFF \
  -DGGML_METAL=OFF -DGGML_ACCELERATE=OFF -DGGML_BLAS=OFF \
  -DGGML_OPENMP=OFF -DGGML_NATIVE=OFF -DLLAMA_CURL=OFF \
  -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_TOOLS=OFF -DLLAMA_BUILD_EXAMPLES=OFF
"${CMAKE:-cmake}" --build "$native" --target llama -j4
if [ "$platform" = iphoneos ]; then
  destination='generic/platform=iOS'
  signing=(-allowProvisioningUpdates "DEVELOPMENT_TEAM=${BF_TEAM:?Set your Apple development team}")
else
  destination='generic/platform=iOS Simulator'
  signing=(CODE_SIGNING_ALLOWED=NO)
fi
xcodebuild -project "$root/BeanFitPocket.xcodeproj" -scheme BeanFitPocket \
  -configuration Release -sdk "$platform" -destination "$destination" \
  -derivedDataPath "$BF_OUTPUT/$platform" "${signing[@]}" \
  "BF_LLAMA_SOURCE=$BF_LLAMA_SOURCE" "BF_LLAMA_BUILD=$native"
