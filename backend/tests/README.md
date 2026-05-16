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

Do not use global Python for this repository.
