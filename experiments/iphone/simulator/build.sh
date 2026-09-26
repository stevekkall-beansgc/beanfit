#!/bin/sh
# Build a CPU-only command-line probe for iOS Simulator from pinned llama.cpp.
# Arguments: llama.cpp source directory, cmake binary, output build directory.
# Does not download assets, boot a simulator or install on any physical device.
set -eu
if [ "$#" -ne 3 ]; then
  echo 'usage: sh build.sh LLAMA_SOURCE CMAKE_BINARY BUILD_DIRECTORY' >&2
  exit 2
fi
"$2" -S "$1" -B "$3" \
  -DCMAKE_SYSTEM_NAME=iOS -DCMAKE_OSX_SYSROOT=iphonesimulator \
  -DCMAKE_OSX_ARCHITECTURES=arm64 -DCMAKE_OSX_DEPLOYMENT_TARGET=26.0 \
  -DCMAKE_BUILD_TYPE=Release -DCMAKE_MACOSX_BUNDLE=OFF \
  -DBUILD_SHARED_LIBS=OFF -DGGML_METAL=OFF -DGGML_ACCELERATE=OFF \
  -DGGML_BLAS=OFF -DGGML_OPENMP=OFF -DGGML_NATIVE=OFF \
  -DLLAMA_CURL=OFF -DLLAMA_BUILD_SERVER=OFF -DLLAMA_BUILD_TESTS=OFF \
  -DLLAMA_BUILD_TOOLS=OFF -DLLAMA_BUILD_EXAMPLES=ON
"$2" --build "$3" --target llama-simple -j 4
