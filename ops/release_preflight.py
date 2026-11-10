"""Repository-root compatibility entry point for read-only release preflight."""
from pathlib import Path
import sys

BACK = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACK))
from app.release_preflight import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
