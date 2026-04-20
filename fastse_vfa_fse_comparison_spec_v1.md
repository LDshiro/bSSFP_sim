# Fast SE / VFA-FSE Comparative Implementation Specification v1

## 0. Purpose and scope

This document specifies a **comparison-oriented** implementation of **Fast SE** and **VFA-FSE** on top of an **existing isochromat-based Bloch solver** that is already capable of steady-state calculations for b-SSFP.

The implementation target is not only to simulate each sequence family independently, but to compare them under clearly controlled conditions for:

- signal evolution,
- image contrast,
- point-spread behavior,
- scan time,
- RF power / SAR proxy,
- motion / FID sensitivity, and
- **SNR efficiency** and **CNR efficiency**.

The intended use is:

1. design or import a Fast SE or VFA-FSE pulse train,
2. simulate the sequence with the **same forward model**,
3. reconstruct the relevant k-space weighting or image-domain quantity, and
4. report matched-condition comparison metrics.

The **canonical forward model** in this specification is the **isochromat solver**.  
An **EPG reference module** is still recommended for two purposes:

- generating VFA trains from published design rules, and
- validating the isochromat implementation against published EPG results.

---

## 1. Key design decision

The previous document was centered on **VFA-FSE sequence design**.  
This document is restructured around a broader comparison harness with five layers:

1. **Common sequence abstraction layer**
2. **Isochromat forward model**
3. **Fast SE and VFA-FSE family-specific parameter layers**
4. **Comparison-condition layer**
5. **Evaluation / reporting layer**

This change is necessary because a meaningful Fast SE vs VFA-FSE comparison cannot be made from flip-angle trains alone. At minimum, the implementation must also standardize:

- which echo time definition is being matched,
- how scan time is counted,
- how noise is modeled,
- how k-space coverage is matched,
- how SNR efficiency is normalized, and
- how motion, PSF, and FID artifacts are quantified.

---

## 2. Provenance and literature map

To keep the implementation traceable, each section should be considered grounded in the following source families.

- **[H2004]** Hennig, Weigel, Scheffler. *Calculation of Flip Angles for Echo Trains With Predefined Amplitudes With the Extended Phase Graph (EPG)-Algorithm*.  
  Used for inverse EPG design of prescribed echo envelopes, constant-amplitude trains, and SPSS / TRAPS preparation logic.

- **[W2014]** Weigel. *Extended Phase Graphs: Dephasing, RF Pulses, and Echoes – Pure and Simple.*  
  Used for EPG state conventions, shift operators, CPMG modeling, and cross-checks between isochromat and EPG behavior.

- **[WH2006]** Weigel, Hennig. *Contrast Behavior and Relaxation Effects of Conventional and Hyperecho-TSE Sequences at 1.5 and 3 T.*  
  Used for \( f_t \), effective T2 contribution, TE correction, and SAR-relative benchmarks for constant-low-flip and TRAPS-style TSE.

- **[B2006]** Busse et al. *Fast Spin Echo Sequences With Very Long Echo Trains.*  
  Used for prescription-specific VFA schedule design, prospective EPG, and **contrast-equivalent TE**.

- **[B2008]** Busse et al. *Effects of Refocusing Flip Angle Modulation and View Ordering in 3D Fast Spin Echo.*  
  Used for explicit control of \(\alpha_{\min}, \alpha_{\text{cent}}, \alpha_{\max}\), 3D view ordering, ETL-independent train counting, PSF analysis, and motion trade-offs.

- **[M2014]** Mugler. *Optimized Three-Dimensional Fast-Spin-Echo MRI.*  
  Used for single-slab 3D-FSE timing logic, short nonselective refocusing pulses, mixed-ESP slab-selective variants, stimulated-echo physics, TE nomenclature issues, and FID artifacts.

- **[S2016]** Sbrizzi et al. *Optimal Control Design of Turbo Spin-Echo Sequences.*  
  Used for optional future direct optimization, parameter grouping, and adjoint-based gradient computation.

- **[G2021]** Guenthner et al. *A unifying view on extended phase graphs and Bloch simulations for quantitative MRI.*  
  Used for future slice-profile / hybrid Bloch-EPG extensions and for understanding how a Bloch/isochromat solver and EPG can be bridged.

---

## 3. Comparison philosophy

### 3.1 Two comparison scopes must be supported

The implementation shall support two distinct scopes.

#### 3.1.1 `comparison_scope = "physics_only"`

This mode isolates the effect of the **refocusing strategy itself**.  
Both sequence families are simulated with the same:

- dimensionality,
- FOV,
- resolution,
- coverage,
- ETL or effective data budget,
- echo spacing (if explicitly forced),
- k-space mapping, and
- noise model.

Typical use case:

- compare `FASTSE_CONST` vs `VFA_FSE_B2008` in **single-slab 3D** with the same \(k_y,k_z\) grid.

This mode answers:

> “How much of the difference is caused by variable flip-angle physics rather than by protocol geometry?”

#### 3.1.2 `comparison_scope = "protocol_realistic"`

This mode allows the sequence families to retain their **natural clinical form**.  
Typical use case:

- compare **2D multi-slice Fast SE** against **single-slab 3D VFA-FSE**.

This mode answers:

> “Given clinically realistic implementations, which protocol has higher SNR efficiency under matched contrast, coverage, or scan-time conditions?”

### 3.2 Mandatory comparison reports

The software shall support at least the following comparison modes.

- `matched_TE_contrast`
- `matched_scan_time`
- `matched_SAR`
- `matched_voxel`
- `matched_resolution`
- `matched_coverage`

At minimum, the reporting layer shall be able to generate the following three standard reports:

#### Report A — matched contrast
Match:

\[
TE_{\text{contrast},A} \approx TE_{\text{contrast},B}
\]

and also match voxel size.

#### Report B — matched time and coverage
Match:

\[
T_{\text{scan},A} \approx T_{\text{scan},B},
\qquad
\Omega_A \approx \Omega_B
\]

where \(\Omega\) denotes anatomical coverage.

#### Report C — matched SAR and contrast
Match:

\[
SAR_A \approx SAR_B,
\qquad
TE_{\text{contrast},A} \approx TE_{\text{contrast},B}
\]

These three reports should be considered the minimum comparison set.

---

## 4. Common sequence abstraction layer

### 4.1 Sequence family enumeration

```text
sequence_family:
  {"FASTSE_CONST",
   "FASTSE_CONST_LOW",
   "FASTSE_CONST_RAMP",
   "VFA_FSE_MANUAL",
   "VFA_FSE_B2006",
   "VFA_FSE_B2008"}
```

Interpretation:

- `FASTSE_CONST`  
  Conventional Fast SE / TSE with constant refocusing flip angle, usually \(180^\circ\).

- `FASTSE_CONST_LOW`  
  Constant-low-flip TSE baseline used for continuity with [WH2006].

- `FASTSE_CONST_RAMP`  
  Initial refocusing ramp followed by constant refocusing, e.g. Alsop-type stabilization.

- `VFA_FSE_MANUAL`  
  User-supplied arbitrary refocusing train.

- `VFA_FSE_B2006`  
  Prescription-specific train generated from the Busse 2006 target-envelope method.

- `VFA_FSE_B2008`  
  Clinical 3D-VFA train generated from \(\alpha_{\min}\), \(\alpha_{\text{cent}}\), \(\alpha_{\max}\), and view-order assumptions.

### 4.2 Dimensionality enumeration

```text
dimensionality:
  {"2D_multi_slice", "3D_single_slab", "3D_multi_slab"}
```

### 4.3 Timing realism mode

```text
timing_mode:
  {"user_fixed_ESP", "derive_min_ESP"}
```

- `user_fixed_ESP`  
  Use the user-provided \(ESP\).

- `derive_min_ESP`  
  Derive the minimum feasible \(ESP\) from RF durations, crusher windows, and readout windows.

### 4.4 Initial-condition mode

```text
initial_state_mode:
  {"equilibrium", "carry_over", "periodic_1TR", "periodic_2TR"}
```

Interpretation:

- `equilibrium`  
  Start each train from full equilibrium:
  \[
  \mathbf{M}(t=0) = (0,0,M_0)^T
  \]

- `carry_over`  
  Propagate the end-of-train state through recovery until the next TR.

- `periodic_1TR`  
  Solve for the periodic fixed point over one repetition:
  \[
  \mathbf{M}_{\text{in}} = \mathcal{F}_{TR}(\mathbf{M}_{\text{in}})
  \]

- `periodic_2TR`  
  Solve a two-TR cycle:
  \[
  \mathbf{M}_{\text{in}}^{(1)} = \mathcal{F}_{TR}^{(2)}(\mathbf{M}_{\text{in}}^{(1)})
  \]
  Useful when residual modulated longitudinal states participate every second TR.

Default:

```text
initial_state_mode = "equilibrium"
```

for routine long-TR Fast SE and single-train VFA-FSE design.

---

## 5. Isochromat forward model

### 5.1 State variables

For each tissue \(t\), spatial location \(\mathbf{r}\), and isochromat index \(m\), define the magnetization state at event index \(q\) as:

\[
\mathbf{M}_{t,\mathbf{r},m}^{(q)} =
\begin{bmatrix}
M_{x,t,\mathbf{r},m}^{(q)} \\
M_{y,t,\mathbf{r},m}^{(q)} \\
M_{z,t,\mathbf{r},m}^{(q)}
\end{bmatrix}
\]

It is also convenient to define the complex transverse component:

\[
M_{+,t,\mathbf{r},m}^{(q)} = M_{x,t,\mathbf{r},m}^{(q)} + i\,M_{y,t,\mathbf{r},m}^{(q)}
\]

\[
M_{-,t,\mathbf{r},m}^{(q)} = M_{x,t,\mathbf{r},m}^{(q)} - i\,M_{y,t,\mathbf{r},m}^{(q)}
\]

The equilibrium magnetization is:

\[
M_{0,t} = PD_t
\]

where \(PD_t\) is the proton density scaling for tissue \(t\).

### 5.2 Spatial representations supported

The forward model shall support at least two spatial representations.

#### 5.2.1 `dephasing_model = "effective_1d"`

Each isochromat is assigned a scalar position \(\xi_m\) along an effective dephasing axis:

\[
\xi_m \in \left[-\frac{1}{2}, \frac{1}{2}\right)
\]

This mode is recommended for:

- early development,
- train design,
- signal-evolution studies,
- PSF studies based on effective echo amplitudes.

#### 5.2.2 `dephasing_model = "xyz_moment"`

Each isochromat is assigned a full position vector:

\[
\mathbf{r}_m = (x_m, y_m, z_m)^T
\]

This mode is recommended for:

- explicit readout modeling,
- slice-selective extensions,
- FID artifact studies,
- phase-encoding direction dependence.

Default:

```text
dephasing_model = "effective_1d"
```

for v1 comparison.

### 5.3 RF rotation operator

The real-basis rotation matrices are:

\[
R_x(\alpha)=
\begin{bmatrix}
1 & 0 & 0 \\
0 & \cos\alpha & -\sin\alpha \\
0 & \sin\alpha & \cos\alpha
\end{bmatrix}
\]

\[
R_z(\phi)=
\begin{bmatrix}
\cos\phi & -\sin\phi & 0 \\
\sin\phi & \cos\phi & 0 \\
0 & 0 & 1
\end{bmatrix}
\]

A hard RF pulse with flip angle \(\alpha\) and RF phase \(\phi_{\text{RF}}\) is then modeled as

\[
R(\alpha,\phi_{\text{RF}})
=
R_z(\phi_{\text{RF}})\,R_x(\alpha)\,R_z(-\phi_{\text{RF}})
\]

The exact sign convention may differ depending on the existing solver, but the same convention must be used consistently for:

- excitation,
- refocusing,
- readout phase interpretation, and
- validation cases.

### 5.4 Free precession and relaxation over \(\Delta t\)

Define:

\[
E_1(\Delta t) = e^{-\Delta t/T_1},
\qquad
E_2(\Delta t) = e^{-\Delta t/T_2}
\]

Let the total phase accrued by isochromat \(m\) over \([t, t+\Delta t]\) be

\[
\Delta \phi_m
=
\Delta \omega_m \Delta t
+
\gamma \int_t^{t+\Delta t}\mathbf{G}(\tau)\cdot \mathbf{r}_m \, d\tau
\]

where:

- \(\Delta\omega_m\): off-resonance for isochromat \(m\),
- \(\gamma\): gyromagnetic ratio,
- \(\mathbf{G}(t)\): gradient waveform.

The state update is

\[
\mathbf{M}_{m}(t+\Delta t)
=
\begin{bmatrix}
E_2 \cos\Delta\phi_m & -E_2 \sin\Delta\phi_m & 0 \\
E_2 \sin\Delta\phi_m & E_2 \cos\Delta\phi_m & 0 \\
0 & 0 & E_1
\end{bmatrix}
\mathbf{M}_{m}(t)
+
\begin{bmatrix}
0 \\
0 \\
M_0(1-E_1)
\end{bmatrix}
\]

where \(M_0 = PD_t\) for the tissue being simulated.

### 5.5 Event-based update equation

For event index \(q\), the generic update is:

\[
\mathbf{M}_{m}^{(q+1)}
=
\mathcal{P}_{q}\!\left(
\mathcal{R}_{q}\!\left(
\mathbf{M}_{m}^{(q)}
\right)
\right)
\]

where:

- \(\mathcal{R}_{q}\): RF pulse operator (identity if no RF pulse),
- \(\mathcal{P}_{q}\): free-precession + relaxation operator over the event interval.

### 5.6 Ensemble signal

For a given tissue \(t\) and acquisition time \(t_a\), the net received signal is

\[
s_t(t_a)
=
\sum_{m=1}^{N_{\text{iso}}}
w_m \, c_m \, \left(M_{x,t,m}(t_a) + i M_{y,t,m}(t_a)\right)
\]

where:

- \(w_m\): quadrature or uniform weight for isochromat \(m\),
- \(c_m\): receive-coil sensitivity factor.

In the simplest case,

\[
w_m = \frac{1}{N_{\text{iso}}},
\qquad
c_m = 1
\]

### 5.7 Echo-center and FID sampling times

For each echo \(n\), define:

- \(t_{n,\text{echo}}\): intended echo-center time
- \(t_{n,\text{FID}}\): sampling time immediately after the refocusing RF pulse, corresponding to FID generation.

The simulator must be able to output both

\[
s_{n,\text{echo}} = s(t_{n,\text{echo}})
\]

and

\[
s_{n,\text{FID}} = s(t_{n,\text{FID}})
\]

because VFA-FSE can generate substantial FID components whereas conventional Fast SE with \(180^\circ\) refocusing does not.

---

## 6. EPG reference module (recommended, not mandatory in the core engine)

The isochromat solver is the canonical forward model.  
However, a small EPG reference module is strongly recommended for two tasks:

1. **generating VFA trains**, and
2. **cross-validating idealized CPMG results**.

### 6.1 EPG state triplet

For dephasing order \(k\),

\[
\mathcal{X}_k =
\begin{bmatrix}
F_k \\
F_{-k} \\
Z_k
\end{bmatrix}
\]

with coherent echo signal

\[
s_n = F_0^{(n)}
\]

### 6.2 Shift operator

Using the EPG notation of [W2014], a gradient moment \(\Delta k\) shifts transverse states as

\[
S(\Delta k): F_k \mapsto F_{k+\Delta k},
\qquad
Z_k \mapsto Z_k
\]

For regular CPMG timing, \(\Delta k = 1\) per half-echo interval in the normalized discrete representation.

### 6.3 Relaxation operator

\[
E(\tau;T_1,T_2)
=
\begin{bmatrix}
e^{-\tau/T_2} & 0 & 0 \\
0 & e^{-\tau/T_2} & 0 \\
0 & 0 & e^{-\tau/T_1}
\end{bmatrix}
\]

### 6.4 Prospective inverse EPG reference formula

For prescribed target signal \(I_n\), one reference form of the inverse EPG solution from [H2004] is

\[
\alpha_n
=
2\arctan\!\left(
\frac{
- Z_1 E_1 E_2
\pm
\sqrt{
Z_1^2 E_1^2 E_2^2
-
\left(F_{-2} E_2^2 - I_n\right)
\left(F_0 E_2^2 - I_n\right)
}
}{
F_0 E_2^2 - I_n
}
\right)
\]

where the abbreviated quantities are evaluated at the previous echo:

\[
F_0 = F_0^{e}(n-1),\qquad
F_{-2} = F_{-2}^{e}(n-1),\qquad
Z_1 = Z_1^{e}(n-1)
\]

and

\[
E_1 = e^{-\tau/T_1},\qquad E_2 = e^{-\tau/T_2}
\]

This formula is included as a **reference generator**.  
The comparison framework does **not** require that the core solver use EPG internally.

---

## 7. Sequence-family-specific inputs

### 7.1 Common input block

```text
sequence_family              : enum
dimensionality               : enum
comparison_scope             : {"physics_only", "protocol_realistic"}

alpha_exc_deg                : float
phi_exc_deg                  : float

alpha_ref_train_deg[]        : array | None
phi_ref_train_deg[]          : array

TR_ms                        : float
ESP_ms                       : float | None
ESP1_ms                      : float | None
ESP2_ms                      : float | None
ETL                          : int
Nskip                        : int

rf_selectivity_exc           : {"slice_selective", "nonselective"}
rf_selectivity_ref           : {"slice_selective", "nonselective"}

rf_dur_exc_ms                : float
rf_dur_ref_ms[]              : array | float

crusher_pre_ms               : float
crusher_post_ms              : float
readout_window_ms            : float
readout_center_offset_ms     : float

timing_mode                  : {"user_fixed_ESP", "derive_min_ESP"}

initial_state_mode           : {"equilibrium", "carry_over", "periodic_1TR", "periodic_2TR"}

dephasing_model              : {"effective_1d", "xyz_moment"}
N_iso                        : int
off_resonance_list_hz[]      : array | None
```

### 7.2 Fast SE-specific inputs

```text
alpha_ref_const_deg          : float
startup_ramp_mode            : {"none", "manual"}
startup_ramp_values_deg[]    : array | None

phase_encode_order_2d        : {"linear", "centric", "reverse_centric"}

Nslices                      : int
slice_thickness_mm           : float
Nslice_slots_per_TR          : int

TE_nominal_ms                : float | None
```

Interpretation:

- `alpha_ref_const_deg = 180` corresponds to conventional Fast SE.
- `alpha_ref_const_deg < 180` supports the WH2006 low-flip baseline.
- `startup_ramp_values_deg[]` supports initial stabilization before constant flip operation.

### 7.3 VFA-FSE-specific inputs

```text
vfa_design_mode              : {"MANUAL", "B2006", "B2008"}

alpha_min_deg                : float | None
alpha_cent_deg               : float | None
alpha_max_deg                : float | None
n_cent                       : int | None
n_min                        : int | None

T1_design_ms                 : float | None
T2_design_ms                 : float | None

target_profile_mode          : {"PSS_signal_envelope", "relaxation_specific", "manual"}

S_target                     : float | None
n_hold                       : int | None
p_pre                        : float | None
p_post                       : float | None
alpha_cap_deg                : float | None

view_order_mode_3d           : {"ky_mod", "kr_mod"}

TE_equiv_target_ms           : float | None
```

### 7.4 Noise and efficiency block

```text
sigma0_complex               : float
receiver_bw_hz_per_px        : float
noise_scaling_mode           : {"fixed_sigma", "bw_scaled", "bw_and_gfactor"}
g_factor_scalar              : float | None
g_factor_map                 : array | None
NEX                          : float
gating_efficiency            : float   # 0 < eta <= 1
```

### 7.5 K-space geometry block

```text
FOVx_mm, FOVy_mm, FOVz_mm    : float
Nx, Ny, Nz                   : int

partial_fourier_y            : float
partial_fourier_z            : float

Ry, Rz                       : int
autocal_region_y             : int | None
autocal_region_z             : int | None
autocal_shape                : {"separable", "nonseparable"}

elliptical_mask              : bool
encoding_mode                : {"2D_ky", "3D_ky_kz"}
view_order_mode              : {"linear", "centric", "reverse_centric", "ky_mod", "kr_mod"}
```

---

## 8. Timing model

### 8.1 Generic echo-center definition

If the sequence uses a uniform echo spacing \(ESP\), then the center of echo \(n\) is

\[
t_{n,\text{echo}} = n \, ESP
\]

when the first echo is taken as occurring at \(ESP\).

If the sequence uses mixed timing, such as slab-selective 3D-FSE with a longer first echo spacing and shorter later spacings, then:

\[
t_{1,\text{echo}} = ESP_1
\]

\[
t_{n,\text{echo}} = ESP_1 + (n-1)ESP_2,
\qquad n \ge 2
\]

### 8.2 Minimum-ESP feasibility

When `timing_mode = "derive_min_ESP"`, the implementation shall estimate the minimum feasible echo spacing.

For a uniform-ESP implementation, use the engineering rule

\[
ESP_{\min}
\approx
\max\!\left(
2\,t_{\text{exc}\rightarrow \text{ref1,min}},
\;
\max_n
\left[
\frac{\tau_{\text{RF},n}}{2}
+
t_{\text{read+crusher},n}
+
\frac{\tau_{\text{RF},n+1}}{2}
\right]
\right)
\]

where:

- \(t_{\text{exc}\rightarrow \text{ref1,min}}\): minimum time between the excitation center and first refocusing center,
- \(\tau_{\text{RF},n}\): RF duration of refocusing pulse \(n\),
- \(t_{\text{read+crusher},n}\): combined readout and crusher window around echo \(n\).

For slab-selective 3D-FSE with mixed timing, enforce

\[
ESP_1 \ge 2\,t_{\text{exc}\rightarrow \text{ref1,min}}
\]

\[
ESP_2 \ge \max_n
\left[
\frac{\tau_{\text{RF},n}}{2}
+
t_{\text{read+crusher},n}
+
\frac{\tau_{\text{RF},n+1}}{2}
\right]
\]

### 8.3 Published timing sanity checks

The implementation shall be able to reproduce timing regimes consistent with the literature, such as:

- multi-slab / selective refocusing example:
  \[
  \tau_{\text{ref}} \approx 3.84\ \text{ms},\quad ESP \approx 8.5\ \text{ms}
  \]
- single-slab / nonselective refocusing example:
  \[
  \tau_{\text{ref}} \approx 0.6\ \text{ms},\quad ESP \approx 3.9\ \text{ms}
  \]

These values are not hard constraints for all implementations, but they are important sanity references for the timing model.

---

## 9. Fast SE model

### 9.1 Canonical Fast SE definition

For conventional Fast SE, the refocusing train is

\[
\alpha_n = \alpha_{\text{ref,const}},
\qquad n=1,\dots,ETL
\]

with default

\[
\alpha_{\text{ref,const}} = 180^\circ
\]

and CPMG phase condition enforced.

### 9.2 Optional constant-low-flip baseline

For continuity with [WH2006], the following constant-flip baselines shall be supported:

\[
\alpha_{\text{ref,const}} \in \{150^\circ,120^\circ,90^\circ,60^\circ\}
\]

This is important because the comparison between Fast SE and VFA-FSE should not be restricted to only \(180^\circ\) refocusing. Constant-low-flip TSE provides a bridge between the two sequence families and is also needed for reproducing the measured \(f_t\) and SAR-relative tables.

### 9.3 Optional startup ramp

For a stabilized-constant-flip implementation,

\[
\alpha_1,\alpha_2,\dots,\alpha_{N_{\text{ramp}}}
\]

may differ from \(\alpha_{\text{ref,const}}\), after which

\[
\alpha_n = \alpha_{\text{ref,const}},
\qquad n>N_{\text{ramp}}
\]

This mode is used to model initial-ramp behavior before steady low-flip refocusing.

### 9.4 TE conventions for Fast SE

For conventional Fast SE with \(180^\circ\) refocusing,

\[
TE_{\text{nominal}} = TE_{\text{center-k}} = TE_{\text{contrast}}
\]

to first order.

For constant-low-flip Fast SE, the implementation shall still output

- \(TE_{\text{center-k}}\),
- \(f_t\),
- \(TE_{\text{contrast}}\),

because the apparent T2 weighting is reduced when \(\alpha_{\text{ref,const}} < 180^\circ\).

---

## 10. VFA-FSE model

### 10.1 General definition

For VFA-FSE,

\[
\alpha_n = \alpha_n^{\text{VFA}},
\qquad n=1,\dots,ETL
\]

with \(\alpha_n^{\text{VFA}}\) varying along the train.

The implementation shall support the following generation modes.

### 10.2 `VFA_FSE_B2006`

This mode reproduces the design logic of Busse 2006:

1. rapidly enter a pseudo-steady-state,
2. hold a target signal level,
3. then linearly increase the refocusing angles to a specified maximum.

A reference target recursion is:

\[
s_{\text{target}}(1) = \frac{1}{2}\left(1 + S_{\text{target}}\right)
\]

\[
s_{\text{target}}(n)
=
\frac{1}{2}\left(
s_{\text{target}}(n-1) + S_{\text{target}}
\right)
\qquad n=2,\dots,n_{\text{hold}}
\]

Then after the hold region, the refocusing train is ramped toward \(\alpha_{\max}\).  
The exact implementation may use the prospective EPG inverse design as a helper generator.

### 10.3 `VFA_FSE_B2008`

This mode uses explicit control points

\[
\alpha_{\min},\quad \alpha_{\text{cent}},\quad \alpha_{\max},\quad n_{\text{cent}},\quad ETL
\]

and optionally \(n_{\min}\).  
This mode is recommended for realistic 3D VFA-FSE because it directly controls:

- minimum FA, which affects motion / flow sensitivity,
- center-k-space FA, which affects SNR,
- maximum FA, which affects RF power and late-train behavior.

### 10.4 Numerical target interpolation

For the Busse 2008 style implementation, define control-point amplitudes

\[
(n_1,c_1),\ (n_2,c_2),\ (n_3,c_3),\ (n_4,c_4)
\]

and interpolate between segments with

\[
s_n^{\text{target}}
=
c_a
+
(c_b-c_a)
\left(
\frac{n-n_a}{n_b-n_a}
\right)^{p_j}
\]

with defaults such as

\[
p_{\text{pre}} = 1.5,\qquad p_{\text{post}} = 1.0
\]

### 10.5 Reference PSS-based signal points

If a PSS-signal-envelope implementation is used, the target points may be generated from a numerical static pseudo-steady-state signal function

\[
s_{\text{spss}}(\alpha)
=
\lim_{m\to\infty}
|s_m(\alpha,\alpha,\dots)|
\]

rather than using a closed-form special-function expression.  
This is preferred for implementation robustness.

### 10.6 First refocusing pulse in slab-selective mixed-ESP mode

If slab-selective excitation with nonselective refocusing is implemented, the first refocusing pulse shall satisfy

\[
\alpha_1 \approx 180^\circ
\]

and crusher gradients shall be applied before and after it, because stimulated echoes associated with the long first echo spacing must be suppressed.

---

## 11. K-space mapping and view ordering

### 11.1 2D Fast SE

Let \(\mathcal{K}_y\) denote the set of acquired phase-encoding indices for 2D Fast SE.

The number of phase trains is

\[
N_{\text{phase-trains}}
=
\left\lceil \frac{|\mathcal{K}_y|}{ETL} \right\rceil
\]

The implementation shall support at least

- linear ordering,
- centric ordering,
- reverse-centric ordering.

### 11.2 3D VFA-FSE or 3D Fast SE

Let

\[
\mathcal{K}_{yz}
=
\left\{
(k_y^{(m)},k_z^{(m)})
\right\}_{m=1}^{N_{\text{views}}}
\]

be the acquired \(k_y,k_z\) coordinates.

The number of trains is

\[
N_{\text{trains}}
=
\left\lceil
\frac{N_{\text{views}}}{ETL}
\right\rceil
\]

#### 11.2.1 Linear modulation (`ky_mod`)

Sort by \(k_y\), assign echo index

\[
e(m) = 1 + \left\lfloor \frac{m-1}{N_{\text{trains}}} \right\rfloor
\]

Then within each echo group, sort by \(k_z\) and assign train index.

This mode is primarily for **long-TEeff / T2-weighted** acquisitions.

#### 11.2.2 Radial modulation (`kr_mod`)

Define

\[
k_r = \sqrt{k_y^2 + k_z^2},
\qquad
\theta = \operatorname{atan2}(k_z, k_y)
\]

Sort first by \(k_r\), then within each radial group by \(\theta\), assigning echoes and trains analogously.

This mode is primarily for **short-TEeff / PD or T1-like** acquisitions.

### 11.3 Nonseparable autocalibration and elliptical coverage

The view-ordering implementation shall support:

- elliptical k-space masks,
- nonseparable autocalibration regions,
- partial Fourier,
- \(R_y \times R_z\) acceleration.

These are required because comparison between realistic 3D VFA-FSE protocols otherwise underestimates the achievable efficiency.

---

## 12. Echo-time definitions

The software shall explicitly distinguish **all** of the following.

### 12.1 Nominal TE

\[
TE_{\text{nominal}}
\]

The scanner- or protocol-level nominal TE assigned to the sequence.

### 12.2 Center-k-space TE

\[
TE_{\text{center-k}}
=
t_{n_{\text{center}},\text{echo}}
\]

where \(n_{\text{center}}\) is the echo index mapped to the center of k-space.

### 12.3 Busse contrast-equivalent TE

Compute the total signal

\[
s(n)
\]

and the coherence-only term

\[
f_{\text{coherence}}(n)
\]

by re-running the sequence with relaxation removed:

\[
T_1 = T_2 = \infty
\]

Then define the relaxation factor

\[
f_{\text{relax}}(n)
=
\frac{s(n)}{f_{\text{coherence}}(n)}
\]

and the Busse contrast-equivalent TE

\[
TE_{\text{equiv,Busse}}(n)
=
- T_{2,\text{rep}}
\ln\!\left(
\frac{s(n)}{f_{\text{coherence}}(n)}
\right)
\]

This quantity is mandatory for VFA-FSE comparisons and optional for constant-low-flip Fast SE.

### 12.4 Weigel–Hennig \( f_t \) metric

Define the fractional T2 contribution \(f_t\) through

\[
I(TE)
=
\beta\,PD\,f_a(\text{sPSS})
\exp\!\left(-\frac{f_t\,TE}{T_2}\right)
\exp\!\left(-\frac{(1-f_t)\,TE}{T_1}\right)
\]

Then the contrast-relevant TE is

\[
TE_{\text{contrast,WH}} = f_t \, TE_{\text{center-k}}
\]

In practice, the implementation shall output

\[
f_t
\]

and

\[
TE_{\text{contrast,WH}}
\]

for both sequence families whenever any refocusing flip angle is below \(180^\circ\).

### 12.5 Required comparison rule

For any matched-contrast comparison, the default criterion shall be

\[
|TE_{\text{contrast},A} - TE_{\text{contrast},B}| \le \epsilon_{TE}
\]

with default

\[
\epsilon_{TE} = \max(5\ \text{ms},\ ESP)
\]

and

\[
TE_{\text{contrast}}
=
\begin{cases}
TE_{\text{center-k}}, & \text{for conventional Fast SE with } 180^\circ \\
TE_{\text{equiv,Busse}}, & \text{default for VFA-FSE} \\
TE_{\text{contrast,WH}}, & \text{optional alternate convention}
\end{cases}
\]

---

## 13. Scan-time model

### 13.1 2D Fast SE

Let

- \(\mathcal{K}_y\): acquired phase-encoding indices,
- \(N_{\text{slices}}\): total slice count,
- \(N_{\text{slice-slots/TR}}\): number of slice opportunities per repetition.

Then

\[
N_{\text{phase-trains}}
=
\left\lceil
\frac{|\mathcal{K}_y|}{ETL}
\right\rceil
\]

\[
N_{\text{slice-groups}}
=
\left\lceil
\frac{N_{\text{slices}}}{N_{\text{slice-slots/TR}}}
\right\rceil
\]

\[
T_{\text{scan,2D}}
=
\frac{
TR \cdot N_{\text{phase-trains}} \cdot N_{\text{slice-groups}} \cdot NEX
}{
\eta_{\text{gating}}
}
\]

where

\[
0 < \eta_{\text{gating}} \le 1
\]

is gating efficiency.

### 13.2 3D VFA-FSE or 3D Fast SE

Let

\[
N_{\text{views}} = |\mathcal{K}_{yz}|
\]

Then

\[
N_{\text{trains}}
=
\left\lceil \frac{N_{\text{views}}}{ETL} \right\rceil
\]

\[
T_{\text{scan,3D}}
=
\frac{
TR \cdot N_{\text{trains}} \cdot NEX
}{
\eta_{\text{gating}}
}
\]

### 13.3 Matched-scan-time criterion

For `matched_scan_time` comparisons, use

\[
\frac{|T_{\text{scan},A} - T_{\text{scan},B}|}
{\frac{1}{2}(T_{\text{scan},A}+T_{\text{scan},B})}
\le
\epsilon_T
\]

with default

\[
\epsilon_T = 0.02
\]

---

## 14. Noise, SNR, and efficiency model

### 14.1 Noise standard deviation

If a fixed complex noise model is used,

\[
\sigma_n = \sigma_0
\]

If receiver bandwidth scaling is enabled,

\[
\sigma_n
=
\sigma_0
\sqrt{\frac{BW}{BW_0}}
\]

If \(g\)-factor is also included,

\[
\sigma_n
=
\sigma_0
\sqrt{\frac{BW}{BW_0}}
\,
g
\]

If averaging is included,

\[
\sigma_n
=
\sigma_0
\sqrt{\frac{BW}{BW_0}}
\,
\frac{g}{\sqrt{NEX}}
\]

For ROI- or voxel-wise \(g\)-factor maps,

\[
g \rightarrow g(\mathbf{r})
\]

### 14.2 Signal measures

For ROI \(R\),

\[
\overline{S}_R = \frac{1}{|R|}\sum_{\mathbf r \in R} |I(\mathbf r)|
\]

### 14.3 SNR

\[
\mathrm{SNR}_R
=
\frac{\overline{S}_R}{\sigma_n}
\]

### 14.4 CNR

For ROIs \(A\) and \(B\),

\[
\mathrm{CNR}_{A,B}
=
\frac{
\left|
\overline{S}_A - \overline{S}_B
\right|
}{
\sigma_n
}
\]

### 14.5 SNR efficiency

The implementation shall output at least the following efficiency metrics:

\[
\eta_{\text{SNR,time}}
=
\frac{\mathrm{SNR}_R}{\sqrt{T_{\text{scan}}}}
\]

\[
\eta_{\text{SNR,vol}}
=
\frac{\mathrm{SNR}_R \,\Delta v}{\sqrt{T_{\text{scan}}}}
\]

\[
\eta_{\text{CNR,time}}
=
\frac{\mathrm{CNR}_{A,B}}{\sqrt{T_{\text{scan}}}}
\]

where

\[
\Delta v = \Delta x\,\Delta y\,\Delta z
\]

is the voxel volume.

### 14.6 Comparative efficiency ratios

For every pairwise comparison, the implementation shall compute:

\[
R_{\eta,\text{SNR,time}}
=
\frac{
\eta_{\text{SNR,time}}^{\text{VFA-FSE}}
}{
\eta_{\text{SNR,time}}^{\text{FastSE}}
}
\]

\[
R_{\eta,\text{SNR,vol}}
=
\frac{
\eta_{\text{SNR,vol}}^{\text{VFA-FSE}}
}{
\eta_{\text{SNR,vol}}^{\text{FastSE}}
}
\]

\[
R_{\eta,\text{CNR,time}}
=
\frac{
\eta_{\text{CNR,time}}^{\text{VFA-FSE}}
}{
\eta_{\text{CNR,time}}^{\text{FastSE}}
}
\]

These ratios are the primary outputs for the SNR-efficiency comparison study.

---

## 15. RF power and SAR proxies

### 15.1 Flip-angle-squared proxy

A mandatory relative SAR proxy is

\[
SAR_{\alpha^2,\text{rel}}
=
\frac{1}{N_{\text{ref}}}
\sum_{n=1}^{N_{\text{ref}}}
\left(
\frac{\alpha_n}{180^\circ}
\right)^2
\]

For a conventional Fast SE reference with all \(\alpha_n = 180^\circ\),

\[
SAR_{\alpha^2,\text{rel}} = 1
\]

### 15.2 Duration-aware RF power proxy

To distinguish long and short RF pulses, a second proxy shall be supported:

\[
P_{\text{RF,rel}}
=
\sum_{n=1}^{N_{\text{ref}}}
\kappa_n
\frac{\alpha_n^2}{\tau_{\text{RF},n}}
\]

where:

- \(\kappa_n\): shape factor for RF pulse \(n\),
- \(\tau_{\text{RF},n}\): RF duration.

If waveform details are unavailable, use

\[
\kappa_n = 1
\]

### 15.3 Matched-SAR criterion

For `matched_SAR` comparisons, use

\[
\frac{|SAR_A - SAR_B|}{\frac12(SAR_A+SAR_B)} \le \epsilon_{SAR}
\]

with default

\[
\epsilon_{SAR}=0.05
\]

---

## 16. Image-quality and artifact metrics

### 16.1 Echo-envelope error

When a target envelope exists,

\[
\mathrm{RMSE}_{\text{env}}
=
\sqrt{
\frac{1}{N_{\text{enc}}}
\sum_{n}
\left(
|s_n| - s_n^{\text{target}}
\right)^2
}
\]

### 16.2 1D and 2D PSF

Let \(W(k)\) or \(W(k_y,k_z)\) denote the k-space modulation after echo-to-view mapping.

Then

\[
\mathrm{PSF}_{1D}(x)
=
\mathcal{F}^{-1}\{W(k)\}
\]

\[
\mathrm{PSF}_{2D}(y,z)
=
\mathcal{F}_{2D}^{-1}\{W(k_y,k_z)\}
\]

Mandatory summary metrics:

\[
\mathrm{FWHM}
\]

and

\[
\mathrm{SLR}
=
\frac{
\max_{\text{sidelobe}} |\mathrm{PSF}|
}{
\max |\mathrm{PSF}|
}
\]

### 16.3 Motion sensitivity

For constant velocity \(v\) along direction \(\hat{\mathbf u}\),

\[
\mathbf r_m(\tau) = \mathbf r_{m,0} + v \tau \hat{\mathbf u}
\]

and therefore

\[
\Delta \phi_m
=
\Delta \omega_m \Delta t
+
\gamma \int_t^{t+\Delta t} \mathbf G(\tau)\cdot\left(\mathbf r_{m,0}+v\tau\hat{\mathbf u}\right)\,d\tau
\]

Define a relative motion-sensitivity metric

\[
M(v)
=
\frac{|s(v)|}{|s(0)|}
\]

evaluated at the center-k-space echo and optionally across the full train.

### 16.4 FID artifact metric

Define

\[
A_{\text{FID}}
=
\max_n
\frac{|s_{n,\text{FID}}|}{|s_{n,\text{echo}}|}
\]

This metric is mandatory for VFA-FSE and optional for conventional Fast SE.

### 16.5 Stored-longitudinal fraction

As an optional explanatory diagnostic, define

\[
f_Z(n)
=
\frac{
\sum_m w_m |M_{z,m}(t_{n,\text{mid}})|
}{
\sum_m w_m \sqrt{M_{x,m}^2 + M_{y,m}^2 + M_{z,m}^2}
}
\]

where \(t_{n,\text{mid}}\) is a representative time point within echo interval \(n\).

### 16.6 Transverse-usage efficiency

Define

\[
f_{\text{use}}(n)
=
\frac{
|s_{n,\text{echo}}|
}{
\sum_m w_m \sqrt{M_{x,m}^2 + M_{y,m}^2}
}
\]

This helps interpret how efficiently the sequence converts available transverse magnetization into observable echo signal.

### 16.7 B1 sensitivity

For RF amplitude scaling factor \(b\),

\[
\alpha_n^{(b)} = b\,\alpha_n
\]

\[
s_n^{(b)} = \text{ForwardModel}\bigl(\alpha_1^{(b)},\dots,\alpha_N^{(b)}\bigr)
\]

Define the coefficient of variation

\[
CV_{B1}(n)
=
\frac{
\operatorname{std}_{b\in\mathcal B}(|s_n^{(b)}|)
}{
\operatorname{mean}_{b\in\mathcal B}(|s_n^{(b)}|)
}
\]

with a default sweep

\[
\mathcal B = \{0.75, 0.80, \dots, 1.25\}
\]

---

## 17. Comparison outputs

The implementation shall produce the following output groups.

### 17.1 Sequence description output

```text
sequence_family
dimensionality
alpha_exc_deg
alpha_ref_train_deg[]
phi_ref_train_deg[]
TR_ms
ESP_ms / ESP1_ms / ESP2_ms
ETL
Nskip
view_order_mode
```

### 17.2 Timing and contrast output

```text
TE_nominal_ms
TE_center_k_ms
TE_equiv_Busse_ms
ft_WH2006
TE_contrast_WH_ms
Tscan_s
```

### 17.3 Signal and image-quality output

```text
echo_signal_per_tissue[]
FID_signal_per_tissue[]
center_echo_signal_per_tissue
PSF_1D
PSF_2D
FWHM
SLR
motion_metric
FID_metric
B1_robustness_metrics
```

### 17.4 Efficiency and safety output

```text
SAR_rel_alpha2
RF_power_rel
SNR_ROI
CNR_ROI_pair
SNR_eff_time
SNR_eff_vol
CNR_eff_time
ratio_vs_reference
```

### 17.5 Comparison bundle output

For every pairwise comparison, the implementation shall export:

```text
comparison_scope
comparison_mode
parameter_table_A
parameter_table_B
matched_constraints_summary
delta_TE_contrast
delta_scan_time
delta_SAR
delta_voxel
delta_coverage
R_eta_SNR_time
R_eta_SNR_vol
R_eta_CNR_time
```

---

## 18. Validation matrix

The comparison-oriented implementation shall include the following validation cases.

### 18.1 `VAL_W2014_CPMG120_no_relax`

Purpose: validate the basic echo-formation physics of the isochromat solver against a known regular TSE / CPMG example.

Settings:

\[
\alpha_{\text{exc}} = 90^\circ,\qquad
\alpha_{\text{ref}} = 120^\circ,\qquad
T_1=T_2=\infty
\]

Expected early echo amplitudes from the published example:

- first echo:
  \[
  |s_1| \approx 0.75
  \]
- second echo:
  \[
  |s_2| \approx 0.94
  \]
- third echo:
  \[
  |s_3| \approx 0.84
  \]

This test validates that the solver properly reproduces stimulated-echo build-up under regular CPMG timing.

### 18.2 `VAL_H2004_constant_Ic`

Purpose: validate the inverse EPG generator.

Run constant-amplitude design cases

\[
I_c \in \{0.3, 0.6, 0.9\}
\]

and compare the generated flip-angle curves and SPSS approach against [H2004].

### 18.3 `VAL_WH2006_ft_and_SAR`

Purpose: validate low-flip Fast SE and TE-correction logic.

Support at least the following conventional TSE reference sets:

For TE = 80 ms:

\[
f_t(\text{TSE180}) \approx 1.000
\]

\[
f_t(\text{TSE150}) \approx 0.963
\]

\[
f_t(\text{TSE120}) \approx 0.877
\]

\[
f_t(\text{TSE90}) \approx 0.739
\]

\[
f_t(\text{TSE60}) \approx 0.573
\]

and relative SAR proxies approximately

\[
SAR_{\text{rel}} \approx \{1.00,\ 0.70,\ 0.46,\ 0.27,\ 0.13\}
\]

for \(180^\circ,150^\circ,120^\circ,90^\circ,60^\circ\), respectively.

For TE = 134 ms, the implementation should reproduce approximately

\[
f_t(\text{TSE150}) \approx 0.964,\quad
f_t(\text{TSE120}) \approx 0.872,\quad
f_t(\text{TSE90}) \approx 0.727,\quad
f_t(\text{TSE60}) \approx 0.555
\]

This benchmark is important because it ties the Fast SE baseline to experimentally measured contrast behavior.

### 18.4 `VAL_B2006_proposed_schedule`

Purpose: validate prescription-specific VFA schedule generation and TE-equivalent calculation.

Use:

\[
\Delta TE = 4\ \text{ms},
\qquad
N_{\text{echoes}} = 260,
\qquad
\alpha_{\max} = 115^\circ,
\]

\[
T_{1,\text{design}} = 1000\ \text{ms},
\qquad
T_{2,\text{design}} = 100\ \text{ms}
\]

and off-design tissues:

\[
(3000,1500),\ (1500,200),\ (800,80),\ (600,60)\ \text{ms}
\]

The implementation shall reproduce the expected qualitative result:

- high PSF peak,
- limited broadening across off-design tissues,
- one-sided apodization after center-k-space.

It shall also support the validation target:

\[
TE_{\text{center-k}} = 585\ \text{ms}
\quad \Longrightarrow \quad
TE_{\text{equiv,Busse}} \approx 140\ \text{ms}
\]

### 18.5 `VAL_B2008_view_order_and_min_flip`

Purpose: validate 3D view-ordering and the minimum-flip / motion trade-off.

Linear-modulation case:

\[
300 \times 200\ \text{elliptical } (k_y,k_z)\text{ matrix}
\]

\[
\text{autocalibration diameter} = 32
\]

\[
R_y = 2,\qquad R_z = 2
\]

\[
N_{\text{views}} = 12392,\qquad ETL=100,\qquad N_{\text{trains}}=124
\]

\[
\alpha_{\min}=25^\circ,\quad
\alpha_{\text{cent}}=70^\circ,\quad
\alpha_{\max}=120^\circ
\]

\[
ESP = 5\ \text{ms}
\]

Radial-modulation case:

\[
N_{\text{views}} = 7031,\qquad ETL=50,\qquad N_{\text{trains}}=141
\]

\[
\alpha_{\min}=\alpha_{\text{cent}}=50^\circ,\qquad \alpha_{\max}=120^\circ
\]

Expected FWHM increases:

- ky modulation: approximately \(7\%, 12\%, 23\%\) in the modulated direction for the tissue set
  \[
  (T_1,T_2) \in \{(1800,150),(1000,100),(700,60)\}\ \text{ms}
  \]
- kr modulation: approximately \(4\%, 8\%, 15\%\) equally in both directions.

Also validate:

\[
\alpha_{\min}\uparrow \Rightarrow ETL\downarrow,\quad \text{motion loss}\downarrow
\]

while resolution remains comparatively insensitive when \(TE_{\text{eff}}\) is held fixed.

### 18.6 `VAL_M2014_timing_and_FID`

Purpose: validate timing realism and FID artifact behavior.

Mandatory timing references:

- selective refocusing example:
  \[
  \tau_{\text{ref}} \approx 3.84\ \text{ms},\quad ESP \approx 8.5\ \text{ms}
  \]
- nonselective refocusing example:
  \[
  \tau_{\text{ref}} \approx 0.6\ \text{ms},\quad ESP \approx 3.9\ \text{ms}
  \]

Mandatory artifact logic:

- low VFA + short-\(T_1\) tissues can produce large FID signals,
- stronger crushers reduce FID artifacts,
- two averages with \(180^\circ\) phase alternation of refocusing pulses should cancel FID contributions.

### 18.7 Optional future validation

- `VAL_G2021_slice_profile`
- `VAL_S2016_optimal_control`

These are recommended for v2, not required for v1.

---

## 19. Implementation strategy

### 19.1 Recommended architecture

The recommended architecture is:

1. **Isochromat core**  
   Canonical forward simulator for both Fast SE and VFA-FSE.

2. **EPG helper module**  
   Used only for:
   - VFA train synthesis,
   - literature regression tests.

3. **Comparison harness**  
   Applies matched-condition constraints and produces report bundles.

4. **Optional image-domain layer**  
   Builds reconstructed image proxies and ROI metrics from sampled k-space data.

### 19.2 Recommended development order

1. Implement **conventional Fast SE** with \(180^\circ\) refocusing.
2. Validate against `VAL_W2014_CPMG120_no_relax`.
3. Add **constant-low-flip Fast SE**.
4. Add \(f_t\) and \(TE_{\text{contrast}}\) logic and validate against `VAL_WH2006_ft_and_SAR`.
5. Add **VFA train import** (`VFA_FSE_MANUAL`).
6. Add **B2006** and **B2008** train generators.
7. Add **3D view ordering** and `VAL_B2008_view_order_and_min_flip`.
8. Add **noise / SNR efficiency** outputs.
9. Add **FID metric** and `VAL_M2014_timing_and_FID`.

### 19.3 Minimum comparison release criterion

A release candidate may be considered valid only if all of the following are true:

\[
\text{Fast SE baseline validated}
\]

\[
\text{constant-low-flip baseline validated}
\]

\[
\text{VFA train generator validated}
\]

\[
TE_{\text{contrast}} \text{ is reported distinctly from } TE_{\text{center-k}}
\]

\[
\eta_{\text{SNR,time}} \text{ and } \eta_{\text{SNR,vol}} \text{ are exported}
\]

\[
\text{comparison reports A, B, C are generated automatically}
\]

---

## 20. Out of scope for v1

The following are intentionally left to later versions unless already available in the existing solver:

- exact slice-selective RF waveform simulation inside the comparison loop,
- hybrid Bloch-EPG signal model,
- full \(B_1^+\) map optimization of VFA trains,
- pTx online optimization,
- exchange / MT / anisotropic diffusion,
- full image reconstruction including coil covariance and prewhitening.

These are natural extensions, but they should not delay the first robust Fast SE vs VFA-FSE comparison release.

---

## 21. Traceability summary

The following literature-to-spec relationships should be preserved in code comments and documentation.

- **Fast SE baseline, low-flip baseline, \(f_t\), TE correction**  
  \(\rightarrow\) [WH2006]

- **VFA train generation and contrast-equivalent TE**  
  \(\rightarrow\) [B2006]

- **\(\alpha_{\min}, \alpha_{\text{cent}}, \alpha_{\max}\), 3D view ordering, motion-vs-ETL trade-off**  
  \(\rightarrow\) [B2008]

- **single-slab timing, short nonselective refocusing pulses, FID artifacts, mixed-ESP slab-selective logic**  
  \(\rightarrow\) [M2014]

- **EPG validation conventions and CPMG reference behavior**  
  \(\rightarrow\) [W2014], [H2004]

- **future direct optimization**  
  \(\rightarrow\) [S2016]

- **future slice-profile-aware bridge between Bloch and EPG**  
  \(\rightarrow\) [G2021]

### 21.1 Current repository mapping note

The current repository implementation is now split into two layers:

- legacy `bSSFP` GUI/viewer and legacy HDF5 compatibility path
- generic comparison backend for future `BSSFP`, `FASTSE`, and `VFA_FSE` family dispatch

Current code-level ownership is:

- common low-level Bloch / affine numerics  
  \(\rightarrow\) `src/bssfpviz/core/`
- current bSSFP family-specific compilation and execution  
  \(\rightarrow\) `src/bssfpviz/sequences/bssfp/`
- generic experiment / result / comparison contracts  
  \(\rightarrow\) `src/bssfpviz/models/comparison.py`
- generic comparison HDF5 persistence  
  \(\rightarrow\) `src/bssfpviz/io/comparison_hdf5.py`
- generic comparison CLI / workflow  
  \(\rightarrow\) `src/bssfpviz/workflows/compare.py`, `compare_cli.py`

This mapping is intentionally preparatory. `FASTSE` and `VFA_FSE` sequence-family execution is not
implemented yet in this phase.
