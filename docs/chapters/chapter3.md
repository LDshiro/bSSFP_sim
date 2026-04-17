# Chapter 3

## Goal
Chapter 3 implements the exact compute core and stores RK and fixed-point outputs in the
same `SimulationDataset`.

## Bloch Equation
The implemented equation is:

```text
Mdot = A M + b

A = [[-1/T2,  +dw,   -uy],
     [ -dw,  -1/T2,  +ux],
     [ +uy,   -ux,  -1/T1]]

b = [0, 0, M0/T1]^T
```

For one piecewise-constant segment:

```text
Mbar = [Mx, My, Mz, 1]^T
Abar = [[A, b],
        [0, 0]]
Fbar = expm(Abar * dt)
F = Fbar[:3, :3]
g = Fbar[:3, 3]
M_next = F @ M + g
```

## 2TR Superperiod
One superperiod is fixed to:
1. pulse-slot 0 RF dwell `0..Nrf-1`
2. free interval 1
3. pulse-slot 1 RF dwell `0..Nrf-1`
4. free interval 2

So:

```text
n_segments = 2 * Nrf + 2
n_boundaries = 2 * Nrf + 3
```

The readout is taken at:

```text
t_readout = rf_duration_s + free_duration_s / 2
```

## Why RK and Fixed Point Both Exist
- RK45 provides a direct time-integration reference trajectory across many repeated cycles.
- The exact affine fixed-point solve provides the steady orbit without transient burn-in.
- Chapter 3 stores both so later GUI work can compare convergence and visualize agreement.

## Stored Array Shapes
- `rf_xy`: `(n_rf_samples, 2)`
- `reference_time_s`: `(n_reference_time,)`
- `steady_state_time_s`: `(n_steady_time,)`
- `reference_m_xyz`: `(n_acq, n_spins, n_reference_time, 3)`
- `steady_state_orbit_xyz`: `(n_acq, n_spins, n_steady_time, 3)`
- `steady_state_fixed_point_xyz`: `(n_acq, n_spins, 3)`
- `individual_profile_complex`: `(n_acq, n_spins)`
- `sos_profile_magnitude`: `(n_spins,)`

## Run
```bash
python scripts/compute_chapter3_demo.py
```

## Test
```bash
ruff check .
ruff format --check .
mypy src
pytest
```

## Known Limits
- No GUI data viewer yet
- No PyVista / pyqtgraph embedding yet
- No optimizer yet
- No alternative schema-version reader yet; loader accepts only `2.0`
