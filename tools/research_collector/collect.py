#!/usr/bin/env python3
"""Collect public research metadata and optional openly accessible PDFs locally."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError as exc:  # pragma: no cover - exercised by CLI environment
    raise SystemExit("Install requirements with: python -m pip install -r tools/research_collector/requirements.txt") from exc

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = ROOT / "tools" / "research_collector" / "sources.yaml"
USER_AGENT = "NCHU-AIoT-HW2-ResearchCollector/0.1 (public metadata; contact repository owner)"


def fetch(url: str, timeout: int = 20) -> tuple[bytes, str, str]:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read()
        return body, response.headers.get("Content-Type", ""), response.geturl()


def normalize_doi(value: str) -> str:
    value = value.strip()
    if value.lower().startswith("https://doi.org/"):
        value = value[len("https://doi.org/"):]
    elif value.lower().startswith("http://doi.org/"):
        value = value[len("http://doi.org/"):]
    return value.strip().strip("/")


def doi_metadata(doi: str) -> dict[str, Any]:
    encoded = urllib.parse.quote(normalize_doi(doi), safe="/()")
    body, _, _ = fetch(f"https://api.crossref.org/works/{encoded}")
    message = json.loads(body)["message"]
    return {
        "doi": message.get("DOI"),
        "title": (message.get("title") or [None])[0],
        "authors": [" ".join(filter(None, (a.get("given"), a.get("family")))) for a in message.get("author", [])],
        "published": message.get("published-print", message.get("published-online", {})).get("date-parts", [[None]])[0],
        "container": (message.get("container-title") or [None])[0],
        "url": message.get("URL"),
        "source": "Crossref",
    }


def url_metadata(url: str, supplied: dict[str, Any]) -> dict[str, Any]:
    # The collector records public metadata supplied by the researcher; it does not crawl pages.
    return {
        "url": url,
        "title": supplied.get("title"),
        "authors": supplied.get("authors", []),
        "institution": supplied.get("institution"),
        "purpose": supplied.get("purpose"),
        "license_status": supplied.get("license_status", "unknown"),
        "acquisition_status": supplied.get("acquisition_status", "metadata_only"),
        "notes": supplied.get("notes"),
        "summary": supplied.get("summary"),
        "source": "registry",
    }


def save_pdf(url: str, papers_dir: Path) -> dict[str, str]:
    body, content_type, final_url = fetch(url)
    if "application/pdf" not in content_type.lower() and not final_url.lower().endswith(".pdf"):
        raise ValueError(f"Source did not identify itself as a PDF: {url}")
    digest = hashlib.sha256(body).hexdigest()
    papers_dir.mkdir(parents=True, exist_ok=True)
    target = papers_dir / f"{digest}.pdf"
    if not target.exists():
        target.write_bytes(body)
    return {"sha256": digest, "path": str(target.relative_to(ROOT)), "url": final_url}


def load_registry(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = data.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("Registry 'sources' must be a list")
    return sources


def collect(registry: Path, output_root: Path) -> dict[str, Any]:
    local_root = (ROOT / "local").resolve()
    output_root = output_root.resolve()
    if not output_root.is_relative_to(local_root):
        raise ValueError("Research output must remain under the ignored local/ directory")
    records: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()
    papers_dir = local_root / "papers"
    for source in load_registry(registry):
        doi = source.get("doi")
        url = source.get("url")
        if not doi and not url:
            raise ValueError("Each source must include a DOI or URL")
        try:
            metadata = doi_metadata(doi) if doi else url_metadata(url, source)
        except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
            metadata = url_metadata(url or f"https://doi.org/{doi}", source)
            metadata["doi"] = doi
            metadata["acquisition_status"] = "metadata_lookup_failed"
            metadata["error"] = str(exc)
        metadata["id"] = source.get("id")
        metadata["registry_url"] = url
        metadata["purpose"] = source.get("purpose")
        if not metadata.get("authors") and source.get("authors"):
            metadata["authors"] = source["authors"]
        if source.get("institution"):
            metadata["institution"] = source["institution"]
        if source.get("notes"):
            metadata["notes"] = source["notes"]
        if source.get("summary"):
            metadata["summary"] = source["summary"]
        metadata["license_status"] = source.get("license_status", metadata.get("license_status", "unknown"))
        metadata["acquisition_status"] = source.get("acquisition_status", metadata.get("acquisition_status", "metadata_only"))
        pdf_url = source.get("pdf_url")
        if pdf_url:
            try:
                pdf = save_pdf(pdf_url, papers_dir)
                metadata["pdf"] = pdf
                metadata["duplicate_pdf"] = pdf["sha256"] in seen_hashes
                seen_hashes.add(pdf["sha256"])
                metadata["acquisition_status"] = "downloaded"
            except (OSError, ValueError, urllib.error.URLError) as exc:
                metadata["acquisition_status"] = "download_failed"
                metadata["download_error"] = str(exc)
        records.append(metadata)

    output_root.mkdir(parents=True, exist_ok=True)
    report = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "source_count": len(records),
        "records": records,
    }
    (output_root / "collection-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    import_dir = ROOT / "local" / "notebooklm-import"
    import_dir.mkdir(parents=True, exist_ok=True)
    lines = [f"{record.get('title') or record.get('doi') or record.get('url')}: {record.get('url') or record.get('registry_url') or ''}" for record in records]
    (import_dir / "sources.txt").write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    manifest = {
        "created_utc": report["created_utc"],
        "source_count": len(records),
        "sources": [
            {
                "id": record.get("id"),
                "url": record.get("registry_url") or record.get("url"),
                "doi": record.get("doi"),
                "title": record.get("title"),
                "authors": record.get("authors", []),
                "institution": record.get("institution"),
                "license_status": record.get("license_status", "unknown"),
                "acquisition_status": record.get("acquisition_status", "metadata_only"),
                "sha256": (record.get("pdf") or {}).get("sha256"),
                "file": (record.get("pdf") or {}).get("path"),
                "purpose": record.get("purpose"),
                "summary": record.get("summary"),
                "notes": record.get("notes"),
                "error": record.get("error") or record.get("download_error"),
            }
            for record in records
        ],
    }
    (import_dir / "sources_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    report_lines = [
        "# W1P1 Research Collection Report",
        "",
        f"Created (UTC): {report['created_utc']}",
        f"Sources: {len(records)}",
        "",
        "## Source status",
        "",
    ]
    for item in manifest["sources"]:
        report_lines.extend([
            f"### {item.get('title') or item.get('id')}",
            f"- Original URL: {item.get('url')}",
            f"- DOI: {item.get('doi') or 'N/A'}",
            f"- Author/institution: {', '.join(item.get('authors') or []) or item.get('institution') or 'Not recorded'}",
            f"- Purpose: {item.get('purpose') or 'Not recorded'}",
            f"- Summary: {item.get('summary') or 'No summary.'}",
            f"- License: {item.get('license_status')}",
            f"- Acquisition: {item.get('acquisition_status')}",
            f"- File/SHA-256: {item.get('file') or 'None'} / {item.get('sha256') or 'N/A'}",
            f"- Notes: {item.get('notes') or item.get('error') or 'No additional notes.'}",
            "",
        ])
    (import_dir / "collection_report.md").write_text("\n".join(report_lines), encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=ROOT / "local" / "research")
    args = parser.parse_args()
    try:
        report = collect(args.registry, args.output)
    except (OSError, ValueError, urllib.error.URLError, json.JSONDecodeError) as exc:
        print(f"Collection failed: {exc}", file=sys.stderr)
        return 1
    print(f"Collected metadata for {report['source_count']} sources into {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
