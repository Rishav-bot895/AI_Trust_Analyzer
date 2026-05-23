from __future__ import annotations

"""Test bootstrap for backend.

Run tests with the project interpreter:
    .venv\\Scripts\\python.exe -m pytest
"""

import sys
import os
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Shared defaults so importing app.core.config works across test modules.
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://user:pass@localhost:5432/testdb")
os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-supabase-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-supabase-service-role-key")
os.environ.setdefault("SUPABASE_JWT_SECRET", "test-supabase-jwt-secret-32bytes-long")
os.environ.setdefault("SUPABASE_JWT_VERIFY_STRATEGY", "hs256")
