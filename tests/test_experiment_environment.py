import subprocess
import sys
import unittest
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import numpy as np
import pandas as pd
import statsmodels.api as sm
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[1]


class ExperimentEnvironmentTests(unittest.TestCase):
    def test_direct_dependency_pins_are_in_the_resolved_lock(self):
        direct_pins = [
            line.strip().casefold()
            for line in (ROOT / "requirements.in").read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        locked_pins = {
            line.strip().casefold()
            for line in (ROOT / "requirements.lock").read_text(encoding="utf-8").splitlines()
        }
        for pin in direct_pins:
            with self.subTest(pin=pin):
                self.assertIn(pin, locked_pins)

    def test_offline_smoke_command_imports_pinned_libraries(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "python" / "src" / "environment_check.py")],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        for library in ("NumPy", "pandas", "scikit-learn", "statsmodels", "matplotlib"):
            with self.subTest(library=library):
                self.assertIn(library, result.stdout)
        self.assertIn("no model was trained", result.stdout)

    def test_synthetic_data_split_design_matrix_and_plot_render(self):
        rng = np.random.default_rng(2026)
        frame = pd.DataFrame(
            {
                "feature_a": rng.normal(size=24),
                "feature_b": rng.normal(size=24),
            }
        )
        train, test = train_test_split(frame, test_size=0.25, random_state=42)
        design = sm.add_constant(train, has_constant="add")

        self.assertEqual((len(train), len(test)), (18, 6))
        self.assertEqual(design.shape, (18, 3))
        self.assertTrue(np.isfinite(design.to_numpy()).all())

        figure = Figure(figsize=(2, 1))
        canvas = FigureCanvasAgg(figure)
        figure.subplots().plot([0, 1, 2], [1, 0, 1])
        canvas.draw()
        self.assertEqual(canvas.get_width_height(), (200, 100))


if __name__ == "__main__":
    unittest.main()
