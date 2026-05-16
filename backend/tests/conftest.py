from __future__ import annotations

"""Test bootstrap for backend.

Run tests with the project interpreter:
    .venv\Scripts\python.exe -m pytest
"""

import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
