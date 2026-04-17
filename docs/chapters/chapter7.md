# Chapter 7

## Goal
Chapter 7 turns the Chapter 6 playback GUI into a comparison-oriented research tool.

The GUI can now:
- load `primary` and `compare` HDF5 datasets
- switch the active slot between `primary` and `compare`
- overlay profile magnitude and selected-spin time series
- render the active dataset in the 3D scene while overlaying only the compare selected spin
- manage `Δf` bookmarks
- save/load session presets as JSON
- export screenshot bundles

## Active / Compare Sync Rules

### Acquisition sync
The compare acquisition index is clamped to the other dataset size:

```text
mapped_acquisition_index = min(active_acquisition_index, other_n_acq - 1)
```

### Delta-f sync
The compare spin uses nearest `Δf` matching against the active selection:

```text
Δf_canon = Δf_active[i_spin_active]
i_spin_other = argmin_j |Δf_other[j] - Δf_canon|
```

### Frame sync
When frame counts differ, the compare frame is matched by normalized relative position:

```text
if Na <= 1:
    ratio = 0.0
else:
    ratio = i / float(Na - 1)

if Nb <= 1:
    mapped_frame = 0
else:
    mapped_frame = int(round(ratio * float(Nb - 1)))
```

### Mode sync
`reference` and `steady` remain global GUI modes. `primary` and `compare` never carry separate modes.

## Session Presets
Session presets persist:
- primary/compare paths
- active slot
- compare enabled / visible flags
- mode
- acquisition index
- frame index
- fps
- loop state
- selected `Δf`
- bookmarks

Stored JSON fields:

```json
{
  "version": 1,
  "primary_path": "... or null",
  "compare_path": "... or null",
  "active_slot": "primary",
  "compare_enabled": false,
  "compare_visible_in_scene": true,
  "mode": "reference",
  "acquisition_index": 0,
  "frame_index": 0,
  "fps": 15.0,
  "loop": true,
  "selected_delta_f_hz": 0.0,
  "bookmarks_hz": [0.0, 125.0]
}
```

## Screenshot Bundle
`Export Current View Bundle...` writes:
- `main_window.png`
- `scene_panel.png`
- `profile_panel.png`
- `time_series_panel.png`
- `session_state.json`
- `manifest.json`

`scene_panel.png` first tries the panel-specific screenshot path and falls back to a widget grab in
headless or non-OpenGL environments.

## Bookmark Workflow
- `Add current` stores the current canonical `Δf`
- `Remove selected` deletes the selected bookmark
- `Jump` moves the selection to the stored `Δf`
- bookmarks are sorted and deduplicated with `1e-9` tolerance

## Fallback Behavior
When `pyvistaqt` is unavailable, OpenGL fails, or `BSSFPVIZ_DISABLE_3D=1` is set, the scene panel
falls back to a text-based status view. The comparison controller, plots, bookmarks, session load,
and export still work.

## Chapter 8 Candidates
- richer side-by-side compare layouts
- multi-dataset batch export
- movie export
- statistical overlays and difference plots
