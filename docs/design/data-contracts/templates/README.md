# Case Package template for future CLI

This folder gives **minimal illustrative JSON skeletons** for future CLI development, not an actual verified case or a ready-to-publish package. Template values must be replaced with real artifacts; placeholders are deliberately not usable as a production release. Every exported byte count and SHA-256 must be computed from real emitted files after any data sanitization. Use the [compatibility contract](../CASE-PACKAGE-CONTRACT.md) and [published packages](../../../../web/data/current-release.json) as truth.

The skeleton in `package.template.json` deliberately has empty manifest and pending phase paths; a conforming *published* package must pass the acceptance gates before inclusion in `current-release.json`. Do not add fake performance metrics, features or predictions to a template.

Phase document files should conform to the canonical `../schemas/phase-0N.schema.json` where applicable. Phase 5 uses the renamed file `phase-05.schema.json`; do not edit its historic `$id` as a migration side effect.
