import re
import unittest
from pathlib import Path


DOCUMENT = Path(__file__).parents[2] / "docs" / "crisp-dm" / "01-business-understanding.md"
NOTEBOOKLM_SUMMARY = Path(__file__).parents[2] / "docs" / "research" / "notebooklm" / "phase1-research-synthesis.md"


class BusinessUnderstandingDocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content = DOCUMENT.read_text(encoding="utf-8")

    def test_required_sections_and_traceability_are_present(self):
        required_sections = (
            "## 1. Executive Summary",
            "## 2. Business Problem",
            "## 3. Research Questions",
            "## 4. Stakeholders & Use Cases",
            "## 5. Business Objectives",
            "## 6. Data Mining Goals",
            "## 7. Success Criteria",
            "## 8. Assumptions & Constraints",
            "## 9. Risks & Limitations",
            "## 10. HW2 Requirements Traceability",
            "## 11. Phase 2 Entry Criteria",
            "## 14. References",
        )
        for section in required_sections:
            with self.subTest(section=section):
                self.assertIn(section, self.content)

        for requirement in ("SalePrice", "RMSE", "MAE", "R²", "Confidence Interval", "Prediction Interval", "NotebookLM", "ChatGPT", "CRISP-DM"):
            with self.subTest(requirement=requirement):
                self.assertIn(requirement, self.content)

    def test_feature_count_and_evidence_boundaries_are_explicit(self):
        self.assertIn("至少 14 個", self.content)
        self.assertIn("不設 39 個特徵上限", self.content)
        self.assertIn("Owner 已提供 NotebookLM 文獻報告", self.content)
        self.assertIn("尚未進行 EDA", self.content)
        self.assertIn("不自行宣告 Gate 通過", self.content)

    def test_notebooklm_summary_is_attributed_and_exceeds_100_chinese_characters(self):
        content = NOTEBOOKLM_SUMMARY.read_text(encoding="utf-8")
        self.assertIn("Human-reviewed synthesis of Owner-provided", content)
        summary = content.split("## NotebookLM 摘要", 1)[1].split("## 引用來源對照", 1)[0]
        self.assertGreaterEqual(len(re.findall(r"[\u4e00-\u9fff]", summary)), 100)
        self.assertIn("https://doi.org/10.1080/10691898.2011.11889627", content)


if __name__ == "__main__":
    unittest.main()
