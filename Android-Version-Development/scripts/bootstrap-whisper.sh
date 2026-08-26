#!/bin/sh
set -eu

VERSION="v1.9.1"
SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
PROJECT_DIR=$(dirname "$SCRIPT_DIR")
DESTINATION="$PROJECT_DIR/third_party/whisper.cpp"

if [ -f "$DESTINATION/.arabic-transcriber-version" ] && \
   [ "$(sed -n '1p' "$DESTINATION/.arabic-transcriber-version")" = "$VERSION" ]; then
    echo "whisper.cpp $VERSION is already available."
    exit 0
fi

if [ -e "$DESTINATION" ]; then
    echo "Refusing to replace existing $DESTINATION. Move it aside and run this script again." >&2
    exit 1
fi

TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT
ARCHIVE="$TEMP_DIR/whisper.cpp.tar.gz"
curl --fail --location --retry 4 \
    "https://github.com/ggml-org/whisper.cpp/archive/refs/tags/$VERSION.tar.gz" \
    --output "$ARCHIVE"
mkdir -p "$DESTINATION"
tar -xzf "$ARCHIVE" --strip-components=1 -C "$DESTINATION"
echo "$VERSION" > "$DESTINATION/.arabic-transcriber-version"
echo "Installed whisper.cpp $VERSION in $DESTINATION"
