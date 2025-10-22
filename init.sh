#!/usr/bin/env bash
set -euo pipefail
mkdir -p field/timeline out assets/fonts gold tests schema tools scripts .github/workflows release_assets
touch assets/fonts/DejaVuSans.ttf || true
echo "Init complete."
