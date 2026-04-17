# Chapter 1

## Goal
Chapter 1 establishes the minimum project skeleton required for future chapters.
The scope is intentionally limited to a bootable Qt application, basic configuration
models, sample configuration data, and automated quality checks.

## Implemented
- `src` layout package structure for `bssfpviz`
- Minimal `QMainWindow` application with a central placeholder label
- Configuration dataclasses headed by `ProjectConfig` and a YAML loader for a minimal sample file
- Unit tests for imports and configuration loading
- Headless-friendly integration test for Qt application boot
- Tooling setup for `ruff`, `mypy`, `pytest`, and `pre-commit`

## Run
```bash
pip install -e .[dev]
bssfpviz
```

Or:

```bash
python -m bssfpviz.app.main
```

## Test
```bash
ruff check .
ruff format --check .
mypy src
pytest
```

## Exit Criteria For Next Chapter
- Package structure is stable enough to add YAML/HDF5 persistence
- GUI boot remains green in headless test environments
- Configuration model is ready to accept richer chapter-specific fields
- No Bloch solver, 3D viewer, or animation logic has been introduced yet
