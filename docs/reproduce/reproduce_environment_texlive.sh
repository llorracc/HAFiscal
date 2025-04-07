#!/bin/bash

# Don't exit if sourced
(return 0 2>/dev/null) && SOURCED=1 || SOURCED=0
if [ "$SOURCED" -eq 0 ]; then
    set -e
fi

REQUIRED_PKGS=(
    microtype.sty
    xcolor.sty
    fontspec.sty
    geometry.sty
    biblatex.sty
)

has_tlmgr() {
    command -v tlmgr >/dev/null 2>&1
}

has_kpsewhich() {
    command -v kpsewhich >/dev/null 2>&1
}

check_scheme_full() {
    if ! has_tlmgr; then return 1; fi
    tlmgr info scheme-full 2>/dev/null | grep -q "installed: Yes"
}

check_required_packages() {
    if ! has_kpsewhich; then return 1; fi
    for pkg in "${REQUIRED_PKGS[@]}"; do
        if ! kpsewhich "$pkg" >/dev/null; then
            echo "Missing LaTeX package: $pkg"
            return 1
        fi
    done
    return 0
}

echo "🔍 Checking TeX Live installation..."

if check_scheme_full; then
    echo "✅ Full TeX Live installation detected (scheme-full)."
    TEXLIVE_OK=1
elif check_required_packages; then
    echo "⚠️ Partial TeX Live install, but required packages found."
    TEXLIVE_OK=1
else
    echo "❌ TeX Live is incomplete or missing."
    echo
    echo "To install:"
    echo "  Linux: https://tug.org/texlive/"
    echo "  macOS: https://tug.org/mactex/"
    if [ "$SOURCED" -eq 1 ]; then
        return 1
    else
        exit 1
    fi
fi

# Set TEXLIVE_OK in parent shell if sourced
if [ "$SOURCED" -eq 1 ]; then
    export TEXLIVE_OK=1
    return 0
else
    exit 0
fi
