# 第3章用 Codex 指示文

以下の指示に従って、第3章「計算コアを実装し、RK 参照解と定常軌道を同じ器に保存する」を実装してください。

この章は**数式仕様を厳密に実装する章**です。推論で式を補わず、`chapter3_equation_spec.md` の式をそのままコードへ落としてください。

## ゴール
次を満たす計算コアを実装してください。

1. shared base waveform と phase schedule から actual pulse waveforms を作れる
2. Bloch 方程式の RK 参照解を計算できる
3. 厳密 propagator で 2TR 超周期の fixed-point を解ける
4. 定常軌道と readout profile を計算できる
5. acquisition ごとの複素 profile と SOS profile を計算できる
6. 第2章の HDF5 スキーマに実計算結果を保存できる

## 重要方針
- **数式は `chapter3_equation_spec.md` を優先**すること
- shape を docstring とテストで固定すること
- correctness を優先し、無理な最適化をしないこと
- GUI 依存を計算コアへ持ち込まないこと
- 既存の第2章データモデル・HDF5 I/O を必要に応じて拡張してよいが、変更は明示すること

## 実装するファイル
以下を新規追加または更新してください。

### 新規推奨
- `src/bssfpviz/core/bloch.py`
- `src/bssfpviz/core/segments.py`
- `src/bssfpviz/core/propagators.py`
- `src/bssfpviz/core/reference.py`
- `src/bssfpviz/core/steady_state.py`
- `src/bssfpviz/workflows/compute_dataset.py`
- `scripts/compute_chapter3_demo.py`
- `tests/unit/test_bloch_matrices.py`
- `tests/unit/test_propagators.py`
- `tests/unit/test_profiles.py`
- `tests/integration/test_chapter3_pipeline.py`
- `docs/chapters/chapter3.md`

### 既存更新候補
- `src/bssfpviz/models/config.py`
- `src/bssfpviz/models/results.py`
- `src/bssfpviz/io/hdf5_store.py`
- `README.md`

## まずやるべきモデル更新
第2章の `SimulationDataset` が trajectory に acquisition 軸を持っていない場合は、以下の shape に更新してください。

- `reference_m_xyz`: `(n_acq, n_spins, n_reference_time, 3)`
- `steady_state_orbit_xyz`: `(n_acq, n_spins, n_steady_time, 3)`
- `steady_state_fixed_point_xyz`: `(n_acq, n_spins, 3)`
- `individual_profile_complex`: `(n_acq, n_spins)`
- `sos_profile_magnitude`: `(n_spins,)`

また time 軸は
- `reference_time_s`: `(n_reference_time,)`
- `steady_state_time_s`: `(n_steady_time,)`

としてください。

HDF5 側も同じ shape が保存できるよう更新してください。

## 設定モデルの要求
`SimulationConfig` に最低限次が入っていることを確認してください。

- `physics.T1_s`
- `physics.T2_s`
- `physics.M0`
- `sequence.tr_s`
- `sequence.rf_duration_s`
- `sequence.free_duration_s`
- `sequence.n_rf_samples`
- `sequence.flip_angle_rad`
- `sequence.phase_schedule_rad` with shape `(n_acq, 2)`
- `sampling.delta_f_hz`
- `sampling.n_cycles`

もし不足していれば、第3章で追加してください。

## 実装仕様

### 1. base waveform の生成
第3章では、まず shared base waveform を 1 本生成します。

要件:
- shape は `(n_rf_samples, 2)`
- x 成分は Hann envelope を nominal flip angle に合うようスケールする
- y 成分は 0 でよい

nominal flip angle `alpha` に対して、x 成分のスケールは

```text
sum(ux[m] * dt_rf) = alpha
```

を満たすようにしてください。

ここで

```text
dt_rf = rf_duration_s / n_rf_samples
```

です。

関数名候補:
- `make_base_rf_waveform(sequence_config) -> NDArray[np.float64]`

### 2. phase schedule による actual waveform 生成
shared base waveform を acquisition/pulse-slot ごとに位相回転して actual waveform を作ってください。

関数名候補:
- `materialize_actual_waveforms(base_rf_xy, phase_schedule_rad) -> actual_rf_xy`

返り値 shape:
- `(n_acq, 2, n_rf_samples, 2)`

数式は `chapter3_equation_spec.md` の式 4 をそのまま使うこと。

### 3. 1 segment の Bloch 行列
関数:
- `bloch_matrix(ux, uy, delta_omega_rad_s, physics) -> A3`
- `bloch_offset_vector(physics) -> b3`
- `augmented_generator(ux, uy, delta_omega_rad_s, physics) -> A4`

shape:
- `A3`: `(3, 3)`
- `b3`: `(3,)`
- `A4`: `(4, 4)`

式は `chapter3_equation_spec.md` の 2, 3 をそのまま実装すること。

### 4. 1 segment propagator
関数:
- `segment_affine_propagator(ux, uy, delta_omega_rad_s, dt_s, physics) -> tuple[F3, g3, F4]`

ここで
- `F3`: `(3, 3)`
- `g3`: `(3,)`
- `F4`: `(4, 4)`

実装手順:
1. `A4 = augmented_generator(...)`
2. `F4 = scipy.linalg.expm(A4 * dt_s)`
3. `F3 = F4[:3, :3]`
4. `g3 = F4[:3, 3]`

### 5. 2TR 超周期の segment 列を作る
**推論で適当に実装しないこと。** `segments.py` に明示的に実装してください。

関数:
- `build_superperiod_segments(actual_rf_xy, delta_omega_rad_s, config) -> SegmentSequence`

`SegmentSequence` は dataclass でよいです。最低限持つべき要素:
- `segment_dt_s`: `(n_segments,)`
- `segment_ux`: `(n_segments,)`
- `segment_uy`: `(n_segments,)`
- `boundary_time_s`: `(n_segments + 1,)`
- `readout_time_s`: scalar

segment の順序は **必ず** 次:
1. pulse-slot 0 の RF dwell 0..N-1
2. free interval 1
3. pulse-slot 1 の RF dwell 0..N-1
4. free interval 2

segment 数は

```text
n_segments = 2*n_rf_samples + 2
```

です。

boundary 時刻は式仕様どおりに構成してください。

### 6. 超周期 affine map の合成
関数:
- `compose_affine_sequence(segment_dt_s, segment_ux, segment_uy, delta_omega_rad_s, physics) -> tuple[Phi3, c3, F_list, g_list]`

返り値:
- `Phi3`: `(3, 3)`
- `c3`: `(3,)`
- `F_list`: `(n_segments, 3, 3)`
- `g_list`: `(n_segments, 3)`

実装手順:
1. `Phi = eye(3)`
2. `c = zeros(3)`
3. 各 segment に対して `F_j, g_j` を作る
4. 式仕様どおり
   - `Phi <- F_j @ Phi`
   - `c <- F_j @ c + g_j`

### 7. fixed-point solve
関数:
- `solve_fixed_point(Phi3, c3) -> M0_ss`

そのまま

```text
(I - Phi) @ M0_ss = c
```

を `numpy.linalg.solve` で解いてください。

### 8. 定常軌道復元
関数:
- `reconstruct_orbit(M0_ss, F_list, g_list, boundary_time_s) -> orbit_xyz`

shape:
- `orbit_xyz`: `(n_boundaries, 3)`

実装手順は `chapter3_equation_spec.md` の 8 の通りです。

### 9. readout profile
関数:
- `compute_readout_profile(M0_ss, actual_rf_xy_for_one_acq, delta_omega_rad_s, config) -> complex`

実装は推論で省略しないこと。

手順:
1. pulse-slot 0 全体の affine map `P0` を作る
2. free interval 1 の**半分**だけの affine map `Fhalf` を作る
3. 合成して `M_ro = Fhalf(P0(M0_ss))`
4. `Mx + 1j * My` を返す

### 10. RK 参照解
関数:
- `integrate_reference_trajectory(actual_rf_xy_for_one_acq, delta_omega_rad_s, config, physics) -> tuple[t_ref, M_ref]`

shape:
- `t_ref`: `(n_reference_time,)`
- `M_ref`: `(n_reference_time, 3)`

要件:
- `solve_ivp(method="RK45")` を使う
- 参照軌道は `n_cycles` 個の 2TR 超周期を繰り返す
- `t_eval` は steady-state orbit の boundary 時刻列を各 cycle に足し込んだものを使う
- 初期値は `[0, 0, M0]`

piecewise control は

```text
t_mod = t % (2*tr_s)
```

で現在 segment を判定し、その segment に対応する `(ux, uy)` を返す実装にしてください。

### 11. dataset 組み立て
関数:
- `compute_dataset(config) -> SimulationDataset`

処理順序:
1. base waveform 生成
2. actual waveforms 生成
3. delta_f sweep ごとに、acquisition ごとに
   - RK 参照解
   - fixed-point solve
   - steady-state orbit
   - individual profile
4. `sos_profile_magnitude = sqrt(sum(abs(individual)^2, axis=0))`
5. `SimulationDataset` を返す

### 12. demo workflow
- `scripts/compute_chapter3_demo.py` を追加
- デバッグ用の高速パラメータを使って HDF5 を 1 個生成
- 保存先例: `data/generated/chapter3_demo.h5`
- 実行後に profile の要約と `late_cycle_error` を表示

## テスト仕様

### unit test 1: Bloch 行列
`test_bloch_matrices.py`
- `bloch_matrix()` の shape が `(3,3)`
- `augmented_generator()` の shape が `(4,4)`
- `ux=uy=dw=0` で期待する対角要素を持つ

### unit test 2: segment propagator
`test_propagators.py`
- `segment_affine_propagator()` が有限値を返す
- free segment (`ux=uy=0`) に対して、`Mz` が `M0` へ緩和する向きを持つ
- `dt=0` なら `F3=I`, `g3=0` になる

### unit test 3: fixed-point consistency
- `reconstruct_orbit()` の最後の状態が開始点に戻る
- 誤差許容は `1e-10` 程度でよい

### unit test 4: profile identity
- `sos_profile_magnitude == sqrt(sum(abs(individual_profile_complex)^2, axis=0))`

### integration test 1: RK late cycle vs steady orbit
高速設定:
- `T1=0.040 s`
- `T2=0.020 s`
- `TR=0.004 s`
- `rf_duration=0.001 s`
- `free_duration=0.003 s`
- `n_rf=100`
- `flip_angle=pi/3`
- `phase_schedule=[[0,0],[0,pi]]`
- `delta_f_hz=[-12.5, 0, +12.5]`
- `n_cycles=120`

この条件で、各 acquisition / 各 spin について

```text
max_norm(last_cycle_rk - steady_orbit) < 5e-5
```

程度を目標にしてください。

### integration test 2: HDF5 round-trip
- `compute_dataset(config)` の結果を save/load して shape と主要数値が保たれること

## ドキュメント
`docs/chapters/chapter3.md` に以下を必ず書いてください。
- Bloch 方程式の式
- 2TR 超周期の図式説明
- RK と fixed-point の二本立ての理由
- HDF5 に保存する配列 shape
- 既知の制約（まだ GUI は無い、まだ最適化は無い）

README にも第3章の実行方法を追記してください。

## 実装後に Codex が返すべき内容
最終出力には必ず次を含めてください。

1. 変更ファイル一覧
2. 各モジュールの役割
3. 実装した主要関数一覧
4. テスト結果
5. `chapter3_demo.h5` の要約
6. 第4章で GUI がどの dataset を読むべきかの短いメモ
