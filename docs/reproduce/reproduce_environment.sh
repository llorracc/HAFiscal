#!/bin/bash

# Detect whether the script is being sourced
(return 0 2>/dev/null) && SOURCED=1 || SOURCED=0

if [ "$SOURCED" -eq 0 ]; then
    set -e
fi

ENV_NAME="HAFiscal"
ENV_FILE="binder/environment.yml"
REQ_FILE="binder/requirements.txt"
VENV_DIR=".venv_${ENV_NAME}"

MINICONDA_URL="https://docs.conda.io/en/latest/miniconda.html"

has_conda() {
    command -v conda >/dev/null 2>&1
}

has_python() {
    command -v python3 >/dev/null 2>&1 && command -v pip3 >/dev/null 2>&1
}

conda_env_path() {
    conda info --base 2>/dev/null | awk '{print $1}' | xargs -I{} echo "{}/envs/$ENV_NAME"
}

error_exit() {
    echo "Error: $1" >&2
    if [ "$SOURCED" -eq 1 ]; then
        return 1
    else
        exit 1
    fi
}

# ---- Conda Path ----

if has_conda; then
    ENV_PATH=$(conda_env_path)

    if [ -d "$ENV_PATH" ]; then
        echo "Activating existing conda environment '$ENV_NAME'..."
        eval "$(conda shell.bash hook)"
        conda activate "$ENV_NAME"
        return 0 2>/dev/null || exit 0
    fi

    if [ -f "$ENV_FILE" ]; then
        echo "Creating conda environment '$ENV_NAME' from $ENV_FILE..."
        conda env create -f "$ENV_FILE" -n "$ENV_NAME" || error_exit "Conda environment creation failed."

        echo "Activating new conda environment '$ENV_NAME'..."
        eval "$(conda shell.bash hook)"
        conda activate "$ENV_NAME"
        return 0 2>/dev/null || exit 0
    fi
else
    echo "Conda is not installed."
    echo
    echo "⚠️  Preferred setup method is via Miniconda or Conda."
    echo "   Please install it from:"
    echo "     $MINICONDA_URL"
    echo
    echo "📦 Falling back to pip + virtualenv..."
fi

# ---- Python venv fallback ----

if [ -d "$VENV_DIR" ]; then
    echo "Activating existing virtualenv at $VENV_DIR..."
    source "$VENV_DIR/bin/activate"
    return 0 2>/dev/null || exit 0
fi

if [ -f "$REQ_FILE" ]; then
    has_python || error_exit "requirements.txt found but Python3 and/or pip3 not available."

    echo "Creating Python virtualenv in $VENV_DIR..."
    python3 -m venv "$VENV_DIR" || error_exit "Failed to create virtualenv."

    echo "Activating new virtualenv at $VENV_DIR..."
    source "$VENV_DIR/bin/activate"
    pip install --upgrade pip
    pip install -r "$REQ_FILE" || error_exit "pip install failed."

    return 0 2>/dev/null || exit 0
fi

# ---- Nothing usable found ----

error_exit "No environment found and neither $ENV_FILE nor $REQ_FILE exist."
