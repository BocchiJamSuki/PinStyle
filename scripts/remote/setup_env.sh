#!/usr/bin/env bash
# Build the "pinstyle" conda env on the AutoDL server (run from the repo root).
# conda uses the server's mirror channels; pip uses the configured PyPI mirror,
# and the PyTorch index is reached through AutoDL's academic acceleration.
set -euo pipefail
ENV_PREFIX=/root/autodl-tmp/envs/pinstyle
CONDA=/root/miniconda3/bin/conda
export CONDA_PKGS_DIRS=/root/autodl-tmp/conda_pkgs
export PIP_CACHE_DIR=/root/autodl-tmp/pip_cache

if [ ! -x "$ENV_PREFIX/bin/python" ]; then
  "$CONDA" create -y -p "$ENV_PREFIX" --override-channels \
    -c https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main python=3.11 pip
fi
"$ENV_PREFIX/bin/python" -m pip install --timeout 60 --retries 10 -r requirements.txt
"$ENV_PREFIX/bin/python" -m pip install -e .
"$ENV_PREFIX/bin/python" -m pip freeze --exclude-editable > requirements.lock.txt
echo "SETUP_DONE"
