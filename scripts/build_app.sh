#!/bin/bash
# Build SwissTaxAgent.app and optionally install to /Applications
set -e

APP_NAME="SwissTaxAgent"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build"
APP_PATH="$BUILD_DIR/$APP_NAME.app"
ICON_PATH="$APP_PATH/Contents/Resources/AppIcon.icns"

echo "▶ Building $APP_NAME.app …"

# ── Clean ──────────────────────────────────────────────────────────────────
rm -rf "$APP_PATH"
mkdir -p "$APP_PATH/Contents/MacOS"
mkdir -p "$APP_PATH/Contents/Resources"

# ── Icon ───────────────────────────────────────────────────────────────────
echo "  Generating icon…"
python3 "$PROJECT_DIR/scripts/make_icon.py" "$ICON_PATH"

# ── Launcher script ────────────────────────────────────────────────────────
LAUNCHER="$APP_PATH/Contents/MacOS/$APP_NAME"
cat > "$LAUNCHER" << SCRIPT
#!/bin/bash
PROJECT_DIR="$PROJECT_DIR"
cd "\$PROJECT_DIR"

# Locate streamlit (venv → pyenv → homebrew → system)
find_streamlit() {
    for candidate in \\
        "\$PROJECT_DIR/.venv/bin/streamlit" \\
        "\$PROJECT_DIR/venv/bin/streamlit" \\
        "\$HOME/.pyenv/shims/streamlit" \\
        "/opt/homebrew/bin/streamlit" \\
        "/usr/local/bin/streamlit"
    do
        [ -f "\$candidate" ] && echo "\$candidate" && return
    done
    # Last resort: PATH (may not be set when launched from Finder)
    command -v streamlit 2>/dev/null || true
}

STREAMLIT=\$(find_streamlit)

if [ -z "\$STREAMLIT" ]; then
    osascript -e 'display dialog "streamlit not found.\n\nOpen a terminal and run:\n  pip install -r requirements.txt" buttons {"OK"} default button "OK" with icon stop'
    exit 1
fi

# Open a Terminal window and run the app
osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '\$PROJECT_DIR' && '\$STREAMLIT' run app.py"
end tell
EOF
SCRIPT

chmod +x "$LAUNCHER"

# ── Info.plist ─────────────────────────────────────────────────────────────
cat > "$APP_PATH/Contents/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleName</key>
    <string>SwissTaxAgent</string>
    <key>CFBundleDisplayName</key>
    <string>SwissTaxAgent</string>
    <key>CFBundleIdentifier</key>
    <string>com.salvatoreviticchie.swisstaxagent</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundleExecutable</key>
    <string>SwissTaxAgent</string>
    <key>CFBundleIconFile</key>
    <string>AppIcon</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>
PLIST

echo "✅ Built: $APP_PATH"
echo ""

# ── Install ────────────────────────────────────────────────────────────────
read -rp "Install to /Applications? [y/N] " yn
if [[ "$yn" =~ ^[Yy]$ ]]; then
    rm -rf "/Applications/$APP_NAME.app"
    cp -r "$APP_PATH" "/Applications/$APP_NAME.app"
    echo "✅ Installed: /Applications/$APP_NAME.app"
    # Refresh icon cache
    touch "/Applications/$APP_NAME.app"
fi
