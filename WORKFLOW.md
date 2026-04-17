# Workflow

## Principle
This repository grows chapter by chapter. Each chapter should add only the minimum
functionality needed for that milestone while keeping README, docs, and tests consistent.

## Standard Loop
1. Define the smallest useful scope for the current chapter.
2. Update the relevant models, workflows, and docs together.
3. Add unit tests for shapes and math contracts.
4. Add integration tests for the end-to-end path introduced in the chapter.
5. Run:

```bash
ruff check .
ruff format --check .
mypy src
pytest
```

## Chapter Status
- Chapter 1: package skeleton and empty GUI
- Chapter 2: data model and HDF5 storage layer
- Chapter 3: exact Bloch core, RK reference, fixed-point steady orbit, profiles, and HDF5 export
- Chapter 4: compute CLI and config-driven HDF5 generation workflow
- Chapter 5+: GUI dataset loading, playback, comparison tools, and richer viewers

## Current Exit Criteria
Chapter 4 is complete when:
- the empty GUI still boots
- exact Chapter 3 compute functions still pass unit and integration tests
- `bssfpviz-compute` writes HDF5 from YAML config and respects overwrite behavior
- HDF5 stores both canonical datasets and Chapter 4 GUI-facing alias datasets
- docs describe the current compute and storage behavior without contradiction
