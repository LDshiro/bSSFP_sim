# Chapter 6

## What This Chapter Adds

Chapter 6 turns the Chapter 5 GUI shell into a synchronized observation tool for one loaded
dataset.

The GUI now shares one playback state across:
- the 3D scene panel
- the profile plot
- the selected-spin time-series plot
- the playback bar

## 3D / 2D Synchronization Design

`DatasetViewModel` normalizes loaded data into one read-only access layer for the GUI.
It hides naming and orientation differences between canonical Chapter 3 datasets and the Chapter 4
alias HDF5 layout.

`PlaybackController` owns the current:
- mode
- acquisition
- spin
- frame
- play/pause state
- loop flag
- playback speed

Panels do not keep their own playback state. They react to controller signals and pull the current
arrays from `DatasetViewModel`.

## Meaning of Mode / Acquisition / Spin / Frame

- `reference`: RK reference trajectory using `reference_time_s` and `reference_m_xyz`
- `steady`: steady-state orbit using `steady_state_time_s` and `steady_state_orbit_xyz`
- acquisition: phase-cycle index
- spin: off-resonance sweep index, treated as the same index as `delta_f_hz`
- frame: current sample along the selected mode's time axis

## DatasetViewModel Responsibilities

`DatasetViewModel` provides:
- frame counts for each mode
- time arrays for each mode
- current `(n_spins, 3)` vectors for the 3D panel
- selected-spin `(n_frames, 3)` series for the time-series plot
- individual complex profiles for each acquisition
- SOS profile
- steady-state orbit overlays
- selected `delta_f_hz`

## PlaybackController State Machine

`PlaybackController` is driven by `QTimer`.

- `toggle_play()` starts or stops timer-driven stepping
- `step_forward()` and `step_backward()` update `frame_index`
- mode changes clamp the frame to the target mode's frame count
- loop on: last frame wraps to 0
- loop off: reaching the last frame stops playback

## 3D Fallback Policy

The GUI prefers `pyvistaqt.QtInteractor`.

Fallback is used when:
- `BSSFPVIZ_DISABLE_3D=1`
- `pyvistaqt` import fails
- OpenGL / Qt surface creation fails

Fallback mode still shows:
- dataset loaded / not loaded
- mode
- acquisition
- frame
- current time
- selected spin and `delta_f_hz`

## Known Limits

- Chapter 6 focuses on observing a single dataset
- 3D playback is interactive but still lightweight
- no comparison view yet
- no movie export yet
- no optimization GUI yet

## Chapter 7 TODO

Chapter 7 should build on:
- `DatasetViewModel` for multi-dataset comparison views
- `PlaybackController` for shared synchronized comparison playback
- `ScenePanel` for overlaying multiple datasets
- `ProfilePanel` for comparison markers and richer inspection controls
