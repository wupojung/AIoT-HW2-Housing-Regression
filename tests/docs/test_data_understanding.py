import unittest
from pathlib import Path


DOCUMENT = Path(__file__).parents[2] / "docs" / "crisp-dm" / "02-data-understanding.md"


class DataUnderstandingDocumentTests(unittest.TestCase):
    def test_target_skewness_is_not_misreported_as_model_diagnostic(self):
        content = DOCUMENT.read_text(encoding="utf-8")
        risk = content.split("## 5. Quality risks & research limitations", 1)[1].split("## 6.", 1)[0]
        self.assertIn("does not establish model residual behavior", risk)
        self.assertIn("Phase 3 may test whether", risk)
        self.assertNotIn("violate homoscedasticity assumptions", risk)
