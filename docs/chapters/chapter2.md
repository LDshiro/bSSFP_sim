# Chapter 2

## Goal
Chapter 2 fixes the data model and HDF5 storage layout that later solver and GUI
chapters will share.

## Implemented
- `SimulationConfig`, `SimulationMetadata`, and `SimulationDataset`
- HDF5 save/load helpers in `io/hdf5_store.py`
- `peek_hdf5_summary()` for lightweight metadata inspection
- `make_demo_dataset()` and `python -m bssfpviz.workflows.demo_dataset`
- Round-trip tests, schema mismatch tests, and shape validation tests

## Run Demo Export
```bash
python -m bssfpviz.workflows.demo_dataset
```

## Test
```bash
ruff check .
ruff format --check .
mypy src
pytest
```

## Exit Criteria For Next Chapter
- Solver outputs can be written directly into `SimulationDataset`
- GUI code can load the HDF5 file without knowing solver internals
- HDF5 schema has clear, stable dataset names
