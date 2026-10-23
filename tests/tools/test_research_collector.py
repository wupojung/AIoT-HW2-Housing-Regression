import json
import shutil
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
            output_root = collect.ROOT / "local" / "research-test"
            try:
                with (
                    patch.object(collect, "url_metadata", side_effect=lambda url, item: {"url": url, "title": item.get("title")}),
                    patch.object(collect, "save_pdf", side_effect=ValueError("not a PDF")),
                ):
                    report = collect.collect(registry_path, output_root)
                self.assertEqual(report["source_count"], 2)
                self.assertEqual(report["records"][1]["acquisition_status"], "download_failed")
                self.assertTrue((output_root / "collection-report.json").exists())
                manifest = json.loads((collect.ROOT / "local/notebooklm-import/sources_manifest.json").read_text(encoding="utf-8"))
                self.assertEqual([source["id"] for source in manifest["sources"]], ["good", "bad-pdf"])
                self.assertTrue((collect.ROOT / "local/notebooklm-import/collection_report.md").exists())
            finally:
                shutil.rmtree(output_root, ignore_errors=True)

    def test_rejects_output_outside_local(self):
        with self.assertRaisesRegex(ValueError, "must remain under"):
            collect.collect(Path("unused.yaml"), collect.ROOT / "docs")


if __name__ == "__main__":
    unittest.main()
