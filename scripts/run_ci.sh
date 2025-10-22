#!/usr/bin/env bash
set -euo pipefail
bash scripts/enforce_env.sh
python -I tools/make_snapshot.py
python -I tools/make_vel_manifest.py
python -I tools/vel_validator.py --artifact field/timeline/latest.json --schema schema/vel_manifest.schema.json VEL_MANIFEST.json
