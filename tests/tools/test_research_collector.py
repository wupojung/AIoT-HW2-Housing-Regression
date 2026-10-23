import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.research_collector import collect


class ResearchCollectorTests(unittest.TestCase):
    def test_one_pdf_failure_does_not_discard_other_sources(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            registry_path = Path(temp_dir) / "sources.yaml"
            registry_path.write_text(
                "sources:\n"
                "  - id: good\n"
                "    url: https://example.org/good\n"
                "    title: Good source\n"
                "  - id: bad-pdf\n"
                "    url: https://example.org/bad\n"
                "    title: PDF unavailable\n"
                "    pdf_url: https://example.org/missing.pdf\n",
                encoding="utf-8",
            )
            local_root = Path(temp_dir) / "local"
            output_root = local_root / "research"
            import_root = Path(temp_dir) / "notebooklm-import"
            with (
                patch.object(collect, "url_metadata", side_effect=lambda url, item: {"url": url, "title": item.get("title")}),
                patch.object(collect, "save_pdf", side_effect=ValueError("not a PDF")),
            ):
                report = collect.collect(registry_path, output_root, import_root, local_root)
            self.assertEqual(report["source_count"], 2)
            self.assertEqual(report["records"][1]["acquisition_status"], "download_failed")
            self.assertTrue((output_root / "collection-report.json").exists())
            manifest = json.loads((import_root / "sources_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual([source["id"] for source in manifest["sources"]], ["good", "bad-pdf"])
            self.assertTrue((import_root / "collection_report.md").exists())

    def test_crossref_failure_is_preserved_in_every_report(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            registry_path = temp_root / "sources.yaml"
            registry_path.write_text(
                "sources:\n"
                "  - id: doi-failure\n"
                "    doi: 10.1234/example\n"
                "    url: https://doi.org/10.1234/example\n"
                "    title: Metadata lookup failure\n"
                "    acquisition_status: metadata_only\n",
                encoding="utf-8",
            )
            local_root = temp_root / "local"
            output_root = local_root / "research"
            import_root = temp_root / "notebooklm-import"
            with patch.object(collect, "doi_metadata", side_effect=ValueError("Crossref unavailable")):
                report = collect.collect(registry_path, output_root, import_root, local_root)
            self.assertEqual(report["records"][0]["acquisition_status"], "metadata_lookup_failed")
            self.assertEqual(report["records"][0]["error"], "Crossref unavailable")
            saved_report = json.loads((output_root / "collection-report.json").read_text(encoding="utf-8"))
            self.assertEqual(saved_report["records"][0]["acquisition_status"], "metadata_lookup_failed")
            manifest = json.loads((import_root / "sources_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["sources"][0]["acquisition_status"], "metadata_lookup_failed")
            self.assertIn("metadata_lookup_failed", (import_root / "collection_report.md").read_text(encoding="utf-8"))

    def test_rejects_research_output_outside_local(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "Research output must remain under"):
                collect.collect(Path(temp_dir) / "unused.yaml", Path(temp_dir) / "research", local_root=Path(temp_dir) / "local")

    def test_rejects_output_outside_local(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            local_root = Path(temp_dir) / "local"
            with self.assertRaisesRegex(ValueError, "Research output must remain under"):
                collect.collect(Path("unused.yaml"), Path(temp_dir) / "research", local_root=local_root)


if __name__ == "__main__":
    unittest.main()
