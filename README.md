# bloch-ssfp-visualizer

`bloch-ssfp-visualizer` is transitioning from a chapter-based bSSFP study tool into a broader
MRI sequence comparison platform.

The current repository now contains two layers:
- a legacy **bSSFP viewer** GUI that remains compatible with the existing Chapter 7 workflow
- a new **generic comparison backend** that can execute sequence-family experiments and write
  comparison-oriented HDF5 bundles

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

## Comparison Backend Status
- `SequenceFamily`, `ExperimentConfig`, `SimulationResult`, and `ComparisonBundle` have been added
- bSSFP is now available as a first-class family inside the generic comparison backend
- `bssfpviz-compare` runs `BSSFP` vs `BSSFP` experiments and writes generic comparison HDF5 bundles
- Fast SE and VFA-FSE are not implemented yet; the backend is prepared for those families next

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

## Compare CLI
```bash
bssfpviz-compare --config examples/configs/comparison_bssfp_minimal.yaml --output data/generated/compare_bssfp.h5
```

This workflow currently supports:
- `comparison_scope = physics_only`
- `BSSFP` vs `BSSFP`
- generic comparison HDF5 output under `/runs/a`, `/runs/b`, and `/comparison`

The current GUI does not open these generic comparison bundles. It remains a legacy bSSFP viewer
for the Chapter 7 dataset layout.

## Core Solver
The compute CLI and the GUI-triggered background runner share a solver pipeline built around a
piecewise-constant Bloch model over a fixed 2TR superperiod. `RunConfig` provides the physics,
sequence, phase-cycle, frequency-sweep, integration, and output-selection inputs; the workflow
turns that config into HDF5 datasets that the GUI later replays.

### Physical Model
For each acquisition and off-resonance sample `Δf`, the solver evolves magnetization
`M = [Mx, My, Mz]^T` with an affine Bloch system:

```text
Mdot = A M + b

A = [[-1/T2,  +Δω,   -uy],
     [ -Δω,  -1/T2,  +ux],
     [ +uy,   -ux,  -1/T1]]

b = [0, 0, M0/T1]^T
Δω = 2πΔf
```

Here `ux` and `uy` are the RF controls in the rotating frame, `T1` and `T2` are the relaxation
constants, `M0` is the equilibrium longitudinal magnetization, and `Δω` is the off-resonance in
rad/s. Each RF dwell and each free-precession interval is treated as one piecewise-constant
segment. For every such segment, the solver builds the augmented affine generator, evaluates the
matrix exponential, and extracts the exact affine update `M_next = F M + g`. That exact segment
propagator is the core primitive used by both the steady-state solve and the fast repeated-grid
reference trajectory path.

### Superperiod and Control Construction
The current solver uses a fixed 2TR superperiod:
1. pulse-slot 0 RF samples
2. free interval
3. pulse-slot 1 RF samples
4. free interval

A shared base RF waveform is first generated and normalized to the requested flip angle. In the
Chapter 4 CLI workflow the waveform can be `hann` or `rect`; acquisition-specific phase cycles
then rotate that base waveform into actual `ux/uy` controls for the two pulses in each
acquisition. The off-resonance sweep is built from `start`, `stop`, and `count`, then converted
internally from `Δf` in Hz to `Δω` in rad/s.

Readout is taken after the first pulse at:

```text
rf_duration_s + readout_fraction_of_free * (TR_s - rf_duration_s)
```

The Chapter 3 midpoint convention corresponds to `readout_fraction_of_free = 0.5`.

### Compute Pipeline
1. Load `RunConfig` from YAML and validate physics, timing, phase-cycle shape, sweep range,
   integration settings, and output flags.
2. Build the base RF waveform and materialize per-acquisition phase-cycled pulse controls.
3. Assemble one explicit 2TR segment sequence for each acquisition and each `Δf` sample.
4. Compose the segment-wise affine propagators into the full superperiod map `(Φ, c)`.
5. Solve `(I - Φ) M_ss = c` to obtain the steady-state magnetization at the start of the
   superperiod.
6. Reconstruct the steady-state orbit by replaying the segment affine maps across the 2TR boundary
   grid.
7. Generate a repeated reference trajectory from the same controls on an explicit shared time
   grid.
8. Evaluate the complex readout signal `Mx + i My` at the configured readout time for every
   acquisition and `Δf`.
9. Reduce the per-acquisition profile magnitudes into an SoS profile over the sweep.
10. Write the selected arrays and metadata to HDF5.

Historical names such as `rk_time_s` and `rk_M` are still used in the workflow and HDF5 outputs.
In the current repeated-grid path, however, those arrays are produced with exact affine substeps on
an explicit shared grid rather than by a pure RK march. RK45 remains in the reference module and
is used as a verification target in tests.

### Core Module Map
- `src/bssfpviz/core/bloch.py`: defines the 3x3 Bloch generator and 4x4 augmented affine form.
- `src/bssfpviz/core/propagators.py`: converts one piecewise-constant segment into exact affine
  maps and composes a full 2TR sequence.
- `src/bssfpviz/core/segments.py`: builds the base RF waveform, applies phase cycling, and expands
  one acquisition into explicit RF/free segments.
- `src/bssfpviz/core/reference.py`: generates repeated reference trajectories, including both the
  RK45 path and the faster exact affine-grid integrator used by current workflows.
- `src/bssfpviz/core/steady_state.py`: solves the superperiod fixed point, reconstructs the
  steady-state orbit, and evaluates the complex readout profile.
- `src/bssfpviz/workflows/run_compute.py`: orchestrates the outer loops over `Δf` and acquisition,
  accumulates solver outputs, and writes HDF5 groups such as `rk`, `steady_state`, and `profiles`.

The main configuration contract lives in `RunConfig`, which separates `physics`, `sequence`,
`phase_cycles`, `sweep`, `integration`, and `output`. The GUI later consumes the stored HDF5
groups rather than recomputing the solver state.

### Main Outputs
- The sweep axis is `delta_f_hz` with shape `(n_delta_f,)`.
- Dense reference trajectories keep the practical axis order
  `(n_delta_f, n_acq, n_time, 3)`, so frequency comes first, then acquisition, then time, then
  `Mx/My/Mz`.
- The steady-state orbit uses the same leading axis order but spans one superperiod instead of the
  repeated reference history.
- Fixed points are stored per `Δf` and acquisition with shape `(n_delta_f, n_acq, 3)`.
- Complex readout profiles are stored per `Δf` and acquisition, then reduced to magnitude and
  SoS-over-acquisition profile summaries.
- When the readout uses the Chapter 3 midpoint convention, the writer also emits canonical Chapter
  3 compatibility datasets so older readers and the GUI adapter layer can consume the same file.

See `HDF5 Usage` below for the dataset names currently read by the GUI.

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
