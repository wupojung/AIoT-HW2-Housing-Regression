"""Phase 1 Business Understanding core for the bounded G2 milestone."""

from __future__ import annotations

import os
import re
from typing import Mapping

from housing_regression.contracts import phase_schema_path, validate_document
from housing_regression.core_utils import PhaseCoreError, emit_json_artifact
from housing_regression.init_config import ConfigError, load_config


_EVIDENCE_FIELDS = (
    ("business_question", "business-question", "Research question"),
    ("source_description", "data-source", "Data source"),
    ("license_or_rights", "data-rights", "Data rights"),
)
_PRIVATE_PATH = re.compile(
    r"(?:[A-Za-z]:[\\/]|(?<!/)/(?!/)[A-Za-z0-9._-]+(?:/[^\s]*)?|"
    r"(?<![A-Za-z0-9_.-])(?:\./)?local/)",
    re.IGNORECASE,
)


def build_phase1(
    config_path: str | os.PathLike[str],
    output_dir: str | os.PathLike[str],
    business_evidence: Mapping[str, str] | None = None,
) -> dict:
    """Write canonical ``content.json``; only explicit complete evidence is included.

    Without an explicit business question, source description, and rights statement,
    the output is ``UNAVAILABLE`` with no invented sections.
    """
    try:
        config = load_config(config_path)
    except ConfigError as exc:
        raise PhaseCoreError("INIT config or source evidence is invalid") from exc

    sections = []
    status = "UNAVAILABLE"
    if business_evidence is not None:
        if not isinstance(business_evidence, Mapping):
            raise PhaseCoreError("business_evidence must be a mapping")
        allowed = {field for field, _, _ in _EVIDENCE_FIELDS}
        if set(business_evidence) - allowed:
            raise PhaseCoreError("business_evidence contains unsupported fields")
        supplied = {field: business_evidence.get(field) for field, _, _ in _EVIDENCE_FIELDS}
        if all(isinstance(value, str) and value.strip() for value in supplied.values()):
            for field, section_id, title in _EVIDENCE_FIELDS:
                body = supplied[field].strip()
                if len(body) > 1000 or _PRIVATE_PATH.search(body):
                    raise PhaseCoreError("business evidence is too long or contains a private path")
                sections.append({"section_id": section_id, "title": title, "body": body})
            status = "MOCK"

    document = {
        "schema_version": "1.0.0",
        "case_id": config.values["case_id"],
        "status": status,
        "sections": sections,
    }
    validate_document(document, phase_schema_path(1))
    emit_json_artifact(document, output_dir, "content.json")
    return document
