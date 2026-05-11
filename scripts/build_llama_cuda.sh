#!/bin/bash
# Build llama.cpp with CUDA support for RTX 2080Ti

set -e

echo "🔨 Building llama.cpp with CUDA support..."
echo ""

# Go to llama.cpp directory
cd /tmp/llama.cpp

# Clean previous build (optional, comment out to reuse cache)
# rm -rf build

# Create build directory
mkdir -p build
cd build

# Configure with CUDA enabled
echo "⚙️  Configuring CMake with CUDA..."
cmake .. \
  -DCMAKE_BUILD_TYPE=Release \
  -DLLAMA_CUDA=ON \
  -DCMAKE_CUDA_ARCHITECTURES=75 \
  -DCMAKE_CUDA_COMPILER=/usr/bin/nvcc

# Build
echo "🏗️  Building (this may take 30-60 minutes)..."
echo ""
cmake --build . --config Release -- -j4

echo ""
echo "✅ Build complete!"
echo ""
echo "Binary location: $(pwd)/bin/llama-server"
ls -lh bin/llama-server
