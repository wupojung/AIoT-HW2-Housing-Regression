"""Acceptance tests for CRISP-DM Phase 3 Data Preparation documentation."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DOC_PATH = REPO_ROOT / "docs" / "crisp-dm" / "03-data-preparation.md"


class DataPreparationDocumentTests(unittest.TestCase):
    """Test suite ensuring docs/crisp-dm/03-data-preparation.md meets all quality gates."""

    @classmethod
    def setUpClass(cls):
        cls.content = DOC_PATH.read_text(encoding="utf-8") if DOC_PATH.is_file() else ""

    def test_document_exists_and_has_required_sections(self):
        self.assertTrue(DOC_PATH.is_file(), "docs/crisp-dm/03-data-preparation.md must exist")
        self.assertGreater(len(self.content), 2000, "Document must not be a stub")

        required_headings = [
            "## 執行摘要 (Executive Summary)",
            "## 1. 資料準備目標與階段邊界 (Objectives & Boundary Gates)",
            "## 2. 資料集分割與防漏機制 (Dataset Splitting & Leakage Prevention)",
            "## 3. 物理結構性缺失與未知遺漏處理 (Structural Absence vs Genuine Missingness)",
            "## 4. 特徵編碼與維度轉換 (Feature Categorization & Encodings)",
            "## 5. 異常值候選與標的隔離 (Target Isolation & 61 IQR Candidates)",
            "## 6. 特徵映射與地端研究產物 (Feature Mapping & Artifacts)",
            "## 7. 研究限制與 Phase 4 候選假設 (Limitations & Phase 4 Hypotheses)",
        ]
        for heading in required_headings:
            with self.subTest(heading=heading):
                self.assertIn(heading, self.content)

    def test_executive_summary_in_traditional_chinese_with_substantive_length(self):
        self.assertIn("## 執行摘要 (Executive Summary)", self.content)
        # Check presence of Chinese characters in executive summary
        cjk_chars = re.findall(r"[\u4e00-\u9fff]", self.content)
        self.assertGreaterEqual(len(cjk_chars), 300, "Document must contain at least 300 Traditional Chinese characters")

    def test_epistemic_status_tags_and_reproducibility_evidence(self):
        self.assertIn("[Verified / 已驗證]", self.content)
        self.assertIn("[Assumed / 假設]", self.content)
        self.assertIn("[Open / 待檢定]", self.content)

        # Split and dimension evidence
        self.assertIn("1,168", self.content)
        self.assertIn("292", self.content)
        self.assertIn("1,459", self.content)
        self.assertIn("42", self.content)
        self.assertIn("79", self.content)
        self.assertIn("246", self.content)
        self.assertIn("61", self.content)

        # Hashes
        self.assertIn("1e18addf81e5e4d347cc17ee6075bbe4a42b7fa26b9e5b063e8f692a5f929d41", self.content)
        self.assertIn("8fdd3d829d4d986b58f845c9553b225e67dd8383624d90fb6ca1d4bed5798c1e", self.content)

    def test_phase_boundaries_strictly_enforced(self):
        # Must clearly forbid model training and feature selection
        self.assertIn("禁止任何模型訓練", self.content)
        self.assertIn("禁止監督式特徵選取", self.content)


if __name__ == "__main__":
    unittest.main()
