#!/bin/sh
# Run from the project on the display Mac. Keeps the model warm until Ctrl-C.
set -eu
cd "$(dirname "$0")"
command -v cmake >/dev/null 2>&1 || { echo "Install build tools first: brew install cmake"; exit 1; }
mkdir -p local-speech
if [ ! -d local-speech/whisper.cpp ]; then
  git clone --depth 1 https://github.com/ggml-org/whisper.cpp.git local-speech/whisper.cpp
fi
cd local-speech/whisper.cpp
if [ ! -x build/bin/whisper-server ]; then
  cmake -B build -DWHISPER_METAL=ON -DWHISPER_BUILD_SERVER=ON
  cmake --build build --config Release -j 4
fi
if [ ! -f models/ggml-small.en.bin ]; then
  sh models/download-ggml-model.sh small.en
fi
exec ./build/bin/whisper-server -m models/ggml-small.en.bin --host 127.0.0.1 --port 8080 -l en -nc
