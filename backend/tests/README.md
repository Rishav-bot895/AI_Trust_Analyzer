# Backend Test Execution

Always run backend Python tests with the project virtual environment interpreter:

```text
.venv\Scripts\python.exe
```

Recommended commands from repository root:

```cmd
.venv\Scripts\python.exe -m pytest backend\tests -q
.venv\Scripts\python.exe -m pytest backend\tests\test_dependencies.py -q
```

Policy guardrail and release-canary coverage lives in:

```text
backend\tests\test_verifier.py
backend\tests\test_judge.py
backend\tests\test_repository.py
backend\tests\test_release_canaries.py
backend\tests\test_correction_outputs.py
```

Do not use global Python for this repository.
