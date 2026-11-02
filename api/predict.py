import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "python" / "src"))

from housing_regression.vercel_car_function import create_handler  # noqa: E402

_BaseHandler = create_handler()


class handler(_BaseHandler):
    pass
