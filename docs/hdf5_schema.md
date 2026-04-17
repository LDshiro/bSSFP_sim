# HDF5 Schema

Chapter 3 stores one `SimulationDataset` per file using schema `2.0`.

```text
/
  attrs:
    schema_version
    created_at_utc
    app_name
    app_version
    git_commit

  /config/physics
    T1_s
    T2_s
    M0
    gamma_rad_per_s_per_T

  /config/sequence
    TR_s
    TE_s
    rf_duration_s
    free_duration_s
    n_rf_samples
    flip_angle_rad
    n_cycles
    phase_schedule_rad            (n_acq, 2)

  /config/sampling
    delta_f_hz                    (n_spins,)
    rk_dt_s
    steady_state_dt_s
    n_reference_steps
    n_steady_state_steps

  /waveforms
    rf_xy                         (n_rf_samples, 2)

  /time
    reference_time_s              (n_reference_time,)
    steady_state_time_s           (n_steady_time,)

  /reference
    M_xyz                         (n_acq, n_spins, n_reference_time, 3)

  /steady_state
    orbit_xyz                     (n_acq, n_spins, n_steady_time, 3)
    fixed_point_xyz               (n_acq, n_spins, 3)

  /profiles
    individual_complex            (n_acq, n_spins)
    sos_magnitude                 (n_spins,)

  /meta
    run_name
    user_notes
```

Notes:
- `rf_xy` is the shared base waveform, not the acquisition-materialized waveforms.
- `reference_time_s` is the repeated superperiod boundary grid for `n_cycles`.
- `steady_state_time_s` is the single-superperiod boundary grid.
