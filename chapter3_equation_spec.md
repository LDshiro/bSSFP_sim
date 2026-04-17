# 第3章 数式仕様メモ

このファイルは Codex に渡す補助仕様です。推論で式を補わず、ここにある式をそのまま実装してください。

## 1. 物理量と単位
- `T1_s`, `T2_s`, `M0`: SI 単位
- `delta_f_hz`: Hz
- `delta_omega_rad_s = 2*pi*delta_f_hz`
- `rf_xy[m, :] = (u_x, u_y)` は **rad/s** 単位
- `tr_s = rf_duration_s + free_duration_s`

## 2. Bloch 行列
単一プール Bloch 方程式は

```text
Mdot = A M + b
```

で、

```text
A = [[-1/T2,  +dw,   -uy],
     [ -dw,  -1/T2,  +ux],
     [ +uy,   -ux,  -1/T1]]

b = [0, 0, M0/T1]^T
```

です。

## 3. 拡大状態

```text
Mbar = [Mx, My, Mz, 1]^T
```

```text
Abar = [[A, b],
        [0, 0]]
```

shape は `(4, 4)`。

1 segment の propagator:

```text
Fbar = expm(Abar * dt)
```

`Fbar` から affine 形式を取り出すと

```text
F = Fbar[:3, :3]
g = Fbar[:3, 3]
```

で、

```text
M_next = F @ M + g
```

です。

## 4. phase schedule と actual waveform
base waveform `rf_xy_base[m, :]` を acquisition `k`、pulse-slot `p` に対して
位相 `phi = phase_schedule_rad[k, p]` だけ回します。

```text
ux_actual = cos(phi) * ux_base - sin(phi) * uy_base
uy_actual = sin(phi) * ux_base + cos(phi) * uy_base
```

## 5. 2TR 超周期の segment 順序
segment は次の順序で並べる。

1. pulse-slot 0 の RF dwell `m = 0 .. Nrf-1`
2. free interval 1 （長さ `free_duration_s`）
3. pulse-slot 1 の RF dwell `m = 0 .. Nrf-1`
4. free interval 2 （長さ `free_duration_s`）

segment 数は

```text
n_segments = 2*Nrf + 2
```

境界点数は

```text
n_boundaries = n_segments + 1 = 2*Nrf + 3
```

## 6. 超周期 propagator
segment affine map を `M_{j+1} = F_j M_j + g_j` とする。

全体写像は

```text
M_out = Phi M_in + c
```

で、segment を順に合成する。

初期値:

```text
Phi = I3
c   = 0
```

segment `j` を左から順に適用する更新は

```text
Phi <- F_j @ Phi
c   <- F_j @ c + g_j
```

最終的な `Phi, c` が 2TR 超周期写像。

## 7. fixed-point
定常状態開始点 `M0_ss` は

```text
(I - Phi) @ M0_ss = c
```

を `numpy.linalg.solve` で解く。

## 8. 定常軌道の復元
境界点軌道は

```text
M[0] = M0_ss
for j in range(n_segments):
    M[j+1] = F_j @ M[j] + g_j
```

で復元する。

## 9. readout 時刻
readout は superperiod 開始から

```text
t_readout = rf_duration_s + free_duration_s / 2
```

に置く。

readout affine map は

1. pulse-slot 0 全体
2. free interval 1 の前半 (`free_duration_s/2`)

を合成して作る。

## 10. profile
readout 磁化 `M_ro = [Mx, My, Mz]^T` に対して

```text
profile_complex = Mx + 1j * My
```

複数 acquisition に対する SOS profile は

```text
sos = sqrt(sum(abs(profile_complex_k)**2, axis=acq))
```

## 11. RK 参照解
`solve_ivp` で 0 から `n_cycles * 2 * tr_s` まで積分する。

時間依存制御は periodic に定義する。時刻 `t` に対して

```text
t_mod = t % (2*tr_s)
```

を使って、今どの segment にいるかを判定する。

参照軌道の保存点は、最低限次でよい。

- 各超周期境界点
- 各 pulse dwell 境界点
- 各 free interval 終点

つまり steady-state orbit と同じ boundary grid を各 cycle で繰り返した時刻列に `t_eval` を置く。

## 12. テスト推奨パラメータ
高速なテスト用パラメータ:

```text
T1_s = 0.040
T2_s = 0.020
M0 = 1.0
tr_s = 0.004
rf_duration_s = 0.001
free_duration_s = 0.003
n_rf_samples = 100
flip_angle_rad = pi/3
phase_schedule_rad = [[0.0, 0.0], [0.0, pi]]
delta_f_hz = [-12.5, 0.0, +12.5]
n_cycles = 120
```

この条件では、late cycle の RK 軌道と fixed-point orbit が十分近くなるはず。
