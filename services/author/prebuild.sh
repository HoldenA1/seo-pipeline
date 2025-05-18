#!/bin/bash

BUILD_DIR="./shared"
STAGING_DIR="./staging"

echo "Preparing staging directory for author..."
rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"

cp -rL "$BUILD_DIR"/. "$STAGING_DIR"/

echo "✅ Prebuild complete. Ready for 'docker-compose build'"