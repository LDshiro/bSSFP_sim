# bloch-ssfp-visualizer

`bloch-ssfp-visualizer` is a chapter-based local tool for studying Bloch / bSSFP behavior.
Chapter 7 turns the GUI into a research-oriented comparison viewer with synchronized 3D/2D
playback, session presets, bookmarks, and screenshot export.

## Chapter 7 Status
- Qt GUI for loading/saving compute configs and running the Chapter 4 workflow
- HDF5 loading for `primary` and `compare` datasets
- synchronized `reference` / `steady-state` playback across 3D and 2D views
- profile magnitude overlay for `primary` and `compare`
- selected-spin `Mx/My/Mz` time-series overlay for `primary` and `compare`
- `primary` / `compare` active-slot switching with nearest-`Δf` comparison mapping
- `Δf` bookmarks with add / remove / jump
- session preset save/load as JSON
- screenshot bundle export with PNG captures and session metadata
- PyVista scene when 3D is available, textual fallback when it is not

## Tech Stack
- Python 3.11+
- PySide6 / Qt Widgets
- NumPy / SciPy
- PyYAML
- h5py
- PyVista + pyvistaqt
- pyqtgraph
- ruff / mypy / pytest / pre-commit

## Repository Layout
```text
bSSFP/
├─ src/bssfpviz/
│  ├─ app/        # application entry point and startup
│  ├─ core/       # Bloch / steady-state solvers and profile computation
│  ├─ gui/        # Qt Widgets-based GUI components and controllers
│  ├─ io/         # HDF5 and JSON persistence
│  ├─ models/     # dataclasses and configuration/result models
│  ├─ viz/        # visualization-facing helpers for 3D/2D views
│  └─ workflows/  # high-level compute and GUI-triggered workflows
├─ tests/
│  ├─ unit/       # focused unit tests
│  └─ integration/ # end-to-end and cross-module checks
├─ examples/configs/  # runnable minimal YAML configs
├─ data/generated/    # local generated outputs kept out of Git except .gitkeep
├─ docs/chapters/     # chapter goals and progress notes
├─ scripts/           # helper scripts for local experiments
└─ pyproject.toml     # package and tool configuration
```

Directory responsibilities:
- `src/bssfpviz/app/`: app entry point and bootstrapping
- `src/bssfpviz/gui/`: Qt Widgets panels, windows, and GUI-side orchestration
- `src/bssfpviz/viz/`: visualization logic shared by scene/plot layers
- `src/bssfpviz/core/`: numerical core for Bloch integration, propagators, and steady state
- `src/bssfpviz/io/`: persistence helpers for HDF5 and session/config serialization
- `src/bssfpviz/models/`: typed configuration and result models
- `src/bssfpviz/workflows/`: compute execution and higher-level operations invoked from CLI/GUI
- `tests/`: unit and integration tests
- `examples/configs/`: hand-editable example configs
- `docs/chapters/`: chapter-by-chapter implementation notes

## Setup
```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
python -m pip install -e .[dev]
```

## GUI
```bash
bssfpviz
```

or:

```bash
python -m bssfpviz.app.main
```

The Chapter 7 GUI supports:
- loading and saving YAML compute configs
- running compute in the background
- opening one `primary` and one `compare` HDF5 dataset
- switching active slot, acquisition, mode, spin, and frame
- playing, pausing, stepping, and scrubbing frames
- comparing profile magnitude and selected-spin time series
- bookmarking `Δf` points
- saving/loading session presets
- exporting screenshot bundles

The default editable compute config used by the GUI is:
[chapter5_default.yaml](/c:/Users/shiro/OneDrive/ドキュメント/Spyder/MISOCP/bSSFP/examples/configs/chapter5_default.yaml)

## Compute CLI
```bash
bssfpviz-compute --config examples/configs/chapter4_default.yaml --output data/generated/ch4_default.h5
```

or:

```bash
python -m bssfpviz.workflows.compute_cli --config examples/configs/chapter4_default.yaml --output data/generated/ch4_default.h5
```

Useful options:
- `--overwrite`
- `--quiet`
- `--summary-json data/generated/ch4_default_summary.json`

## Compare Workflow
1. Launch `bssfpviz`.
2. Use `File/Open Primary Dataset...` to load the main dataset.
3. Use `File/Open Compare Dataset...` to load the comparison dataset.
4. Toggle `compare enabled` and choose the active slot from the comparison controls.
5. Use the playback bar to switch `reference` / `steady-state`, acquisition, spin, and frame.
6. Inspect the profile plot, selected-spin time-series plot, and the synchronized 3D scene.

Comparison synchronization uses:
- acquisition clamp to the compare dataset acquisition count
- nearest `Δf` matching for the compare spin
- normalized frame-position mapping when frame counts differ

## Session Presets and Screenshot Bundles
- `File/Save Session Preset...` writes the current GUI state to JSON.
- `File/Load Session Preset...` restores paths, mode, acquisition, frame, bookmarks, and playback state.
- `File/Export Current View Bundle...` writes PNG captures plus `session_state.json` and `manifest.json`.

Export bundles are typically written under `data/generated/` and contain:
- `main_window.png`
- `scene_panel.png`
- `profile_panel.png`
- `time_series_panel.png`
- `session_state.json`
- `manifest.json`

## 3D Fallback
When 3D is unavailable, set `BSSFPVIZ_DISABLE_3D=1` or run headless. The scene panel falls back
to a textual status view, while playback, plots, metadata, bookmarks, session loading, and export
remain available.

## HDF5 Usage
The GUI reads these datasets when present:
- `/sweep/delta_f_hz`
- `/rk/time_s`
- `/rk/M`
- `/steady_state/orbit_time_s`
- `/steady_state/orbit_M`
- `/steady_state/fixed_points`
- `/profiles/individual_complex_realimag`
- `/profiles/sos_abs`

Canonical Chapter 3 datasets are also supported through the GUI adapter layer.

## Tests
```bash
ruff check .
ruff format --check .
mypy src
pytest
```

Headless GUI tests use:
- `QT_QPA_PLATFORM=offscreen`
- `BSSFPVIZ_DISABLE_3D=1`

## Current Reach
- Chapter 1: package skeleton and GUI boot
- Chapter 2: data model and HDF5 persistence layer
- Chapter 3: exact compute core, steady-state orbit, profile generation, and demo export
- Chapter 4: config-driven compute CLI and data-generation workflow
- Chapter 5: GUI shell for config editing, compute execution, HDF5 loading, and profile inspection
- Chapter 6: synchronized playback across 3D scene, profile plot, and selected-spin time series
- Chapter 7: dual-dataset comparison, session presets, bookmarks, and screenshot export

## Next Chapter
Chapter 8 can extend the comparison GUI with richer side-by-side analysis, batch export, and
publication-oriented visualization polish.
