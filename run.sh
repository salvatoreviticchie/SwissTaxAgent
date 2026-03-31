#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Activate virtualenv if present
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Find streamlit: venv → pyenv → homebrew → system Python
find_streamlit() {
    for candidate in \
        ".venv/bin/streamlit" \
        "venv/bin/streamlit" \
        "$HOME/.pyenv/shims/streamlit" \
        "/opt/homebrew/bin/streamlit" \
        "/usr/local/bin/streamlit" \
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/streamlit"
    do
        [ -f "$candidate" ] && echo "$candidate" && return
    done
    command -v streamlit 2>/dev/null || true
}

STREAMLIT=$(find_streamlit)

if [ -z "$STREAMLIT" ]; then
    echo "❌ streamlit not found. Run: pip3 install -r requirements.txt"
    exit 1
fi

"$STREAMLIT" run app.py
