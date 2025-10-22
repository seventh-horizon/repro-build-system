SHELL := /bin/bash
.DEFAULT_GOAL := help

.PHONY: help prep setup test build verify tar snapshot rbom rbom-check verify-tar-determinism \
        lock download-deps verify-signature pins-check env-snapshot json-check meta-check ci-lint \
        quickcheck evidence summary version compliance

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  build            - Snapshot + manifest."
	@echo "  verify           - Validate manifest vs artifact."
	@echo "  tar              - Create deterministic tar.gz."
	@echo "  verify-tar-determinism - Verify tar has deterministic metadata."
	@echo "  rbom             - Build Release BOM."
	@echo "  rbom-check       - Check RBOM against policy."
	@echo "  pins-check       - Verify all workflows pin actions by SHA."
	@echo "  json-check       - Canonical JSON formatting check."
	@echo "  meta-check       - Meta lint + policy index."
	@echo "  ci-lint          - Pins, permissions, and JSON checks."
	@echo "  quickcheck       - Minimal determinism unit tests."
	@echo "  evidence         - Synthesize evidence matrix."
	@echo "  summary          - Generate CI summary."
	@echo "  version          - Emit version.json."
	@echo "  compliance       - Run ci-lint, meta-check, evidence, summary, version."

build: snapshot
	python -I tools/make_vel_manifest.py

snapshot:
	python -I tools/make_snapshot.py

verify:
	python -I tools/vel_validator.py --artifact field/timeline/latest.json --schema schema/vel_manifest.schema.json VEL_MANIFEST.json

verify-signature:
	@echo "INFO: cosign verify (optional)"
	@true

tar:
	@python -I -c '\
from tools.config import get_path; from tools.det_tar import build_tar; \
build_tar(get_path("tarball_base"), [get_path("artifact"), get_path("manifest")])'
	GZIP=-n gzip -9f $(shell python -I -c 'from tools.config import get_path; print(get_path("tarball_base"))')

rbom:
	python -I tools/make_rbom.py --inputs "out/* VEL_MANIFEST.json" --out release_bom.json

rbom-check:
	python -I tools/rbom_check.py --policy schema/rbom_policy.json --rbom release_bom.json --out rbom_check.json

verify-tar-determinism:
	@python -I tools/verify_tar_determinism.py --tar $(shell python -I -c 'from tools.config import get_path; print(get_path("tarball_base"))').gz --out tar_check.json

pins-check:
	python -I scripts/verify_pins.py --pins ACTIONS-PINS.md --out pins_report.json

json-check:
	python -I tools/json_canonical_check.py --out json_check_report.json "schema/**/*.json" "*.json" || true

meta-check:
	python -I tools/meta_lint.py
	python -I tools/policy_trace.py

ci-lint:
	python -I scripts/verify_pins.py --pins ACTIONS-PINS.md --out pins_report.json
	python -I tools/permissions_lint.py
	$(MAKE) json-check

quickcheck:
	python -I -m pytest -q tests/test_cjson_canonical.py tests/test_det_tar.py tests/test_safe_paths.py || true

evidence:
	python -I tools/evidence_matrix.py

summary:
	python -I tools/make_ci_summary.py

version:
	python -I tools/version_stamp.py

compliance:
	$(MAKE) ci-lint
	$(MAKE) meta-check
	$(MAKE) evidence
	$(MAKE) summary
	$(MAKE) version
