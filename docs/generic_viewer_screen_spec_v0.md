# Generic Viewer Screen Spec v0

## 0. 目的

本仕様は、現行の Chapter 7 bSSFP GUI を土台にしつつ、将来的に `BSSFP` / `FASTSE` / `VFA_FSE`
を同じアプリケーションで扱える **generic sequence viewer** の画面仕様 v0 を定義する。

v0 の主目的は次の 3 点である。

1. 現行の 3D アニメーション表示の描画性能と更新性能を維持する。
2. Fast SE / VFA-FSE を比較するために必要な入力項目と確認項目を整理し、family-aware な GUI
   の骨格を定義する。
3. 既存の legacy bSSFP viewer を壊さずに、generic viewer へ段階的に移行できる画面構成を定義する。

---

## 1. スコープ

### 1.1 v0 で対象とすること

- family-aware な sequence input editor
- `Run A` / `Run B` の比較前提 UI
- sequence preview
  - refocusing flip-angle train
  - timing preview
  - k-space ordering preview
  - derived summary
- simulation result inspector
  - signal evolution
  - timing / contrast summary
  - efficiency / SAR summary
  - PSF / FID / motion / B1 robustness summary
- 既存 3D scene の再利用
- generic result bundle を読むための viewer 側データ契約の定義

### 1.2 v0 で対象外とすること

- Fast SE / VFA-FSE の物理ソルバ実装そのもの
- full image reconstruction workflow
- generic viewer 上での最終的な publication-ready 可視化の磨き込み
- 全 family に対する完全な 3D 表現の最適化

---

## 2. 設計原則

### 2.1 3D scene は保存する

現行の `ScenePanel` は、キャッシュ済み geometry、frame-only update、PyVista fallback を含めて
十分にチューニングされている。このため generic viewer では次の方針を採る。

- 3D scene の内部描画ロジックはできるだけ変更しない
- generic 側では `ScenePanel` に渡す view-model を一般化する
- family 固有の確認項目は 3D scene に押し込まず、inspector 側へ逃がす

### 2.2 入力と確認を分ける

Fast SE / VFA-FSE では、入力値そのものよりも、

- そこから導出される flip train
- timing feasibility
- TE の定義
- scan time
- SAR proxy
- k-space center mapping

の確認が重要である。したがって GUI は `Editor` と `Preview / Inspector` を明確に分離する。

### 2.3 family-aware, but not family-fragmented

family によって必要な項目は変わるが、画面構成は family ごとに別アプリにしない。

- 共通入力は同じ位置に置く
- family 固有入力は `Run A` / `Run B` の中で切り替える
- 結果表示は family 共通の summary と family 固有の detail を併記する

### 2.4 comparison-first

本プロジェクトの目的は sequence 間比較であるため、generic viewer の標準形は
`single-run viewer` ではなく `A/B comparison viewer` とする。

---

## 3. 想定ユースケース

### 3.1 physics-only 比較

- `FASTSE_CONST` と `VFA_FSE_B2008` を同一 geometry で比較する
- same voxel / same coverage / same scan time などの拘束条件を確認する
- echo envelope, PSF, SNR efficiency を比較する

### 3.2 protocol-realistic 比較

- 2D multi-slice Fast SE と 3D single-slab VFA-FSE を比較する
- dimensionality や timing realism を含めて比較する
- scan time と coverage の差を summary で把握する

### 3.3 legacy bSSFP 観察

- 従来の Chapter 7 GUI と同等の 3D / 2D 観察を継続する
- generic viewer の導入後も legacy viewer は当面併存させる

---

## 4. 画面構成

v0 の標準画面は次の 3 カラム + 下段 summary とする。

```text
+--------------------------------------------------------------------------------------+
| Menu / Toolbar                                                                       |
+------------------------+-----------------------------------+-------------------------+
| Left: Experiment       | Center: Animation Workspace       | Right: Inspector Tabs   |
| Editor                 |                                   |                         |
|                        |  +-----------------------------+  |  Sequence               |
|  Common                |  | 3D ScenePanel               |  |  Timing / Contrast      |
|  Run A                 |  |  existing fast path kept    |  |  Results                |
|  Run B                 |  +-----------------------------+  |  Comparison             |
|  Comparison            |  +-----------------------------+  |  Metadata               |
|  Advanced              |  | Playback + Selection Strip  |  |  Log                    |
|                        |  +-----------------------------+  |                         |
+------------------------+-----------------------------------+-------------------------+
| Bottom: Comparison Summary / Constraint Check / Run Status / Export                  |
+--------------------------------------------------------------------------------------+
```

### 4.1 Left: Experiment Editor

役割:

- 入力値の編集
- family 切替
- compare 条件の設定
- sequence preview の更新トリガ

### 4.2 Center: Animation Workspace

役割:

- 既存 3D scene を使った magnetization trajectory 表示
- current selection の再生
- `Run A` / `Run B` の overlay 表示

### 4.3 Right: Inspector Tabs

役割:

- 入力値から導出された preview の確認
- 実行結果の定量確認
- 比較レポートの確認

### 4.4 Bottom: Summary Bar

役割:

- matched constraints の達成状況
- run status
- current selection summary
- export / snapshot 操作

---

## 5. Left Pane: Experiment Editor

Left pane は `Common`, `Run A`, `Run B`, `Comparison`, `Advanced` の 5 セクションで構成する。

### 5.1 Common

共通物理・比較条件を置く。

必須項目:

| 項目 | 役割 |
| --- | --- |
| `comparison_scope` | `physics_only` / `protocol_realistic` |
| `dimensionality` | `2D_multi_slice` / `3D_single_slab` / `3D_multi_slab` |
| tissue presets | 比較対象 tissue の選択または追加 |
| `noise_scaling_mode` | SNR/CNR 比較の前提 |
| `NEX` | averaging |
| `gating_efficiency` | 実 scan time 換算 |
| geometry block | FOV, matrix, voxel, coverage |

表示上の要件:

- tissue は 1 つではなく複数行対応とする
- geometry は voxel size と coverage が同時に見えるようにする
- `Common` で設定した値を `Run A/B` が参照できるようにする

### 5.2 Run A / Run B

各 run は同じ UI 構造を持ち、`sequence_family` で family 固有ブロックを切り替える。

共通項目:

| 項目 | 役割 |
| --- | --- |
| `sequence_family` | family 選択 |
| `alpha_exc_deg`, `phi_exc_deg` | excitation |
| `TR_ms` | repetition time |
| `ETL` | echo train length |
| `Nskip` | prescan / startup skip |
| `timing_mode` | `user_fixed_ESP` / `derive_min_ESP` |
| `initial_state_mode` | equilibrium / carry-over / periodic |
| `dephasing_model` | `effective_1d` / `xyz_moment` |
| `N_iso` | isochromat count |
| off-resonance settings | list / preset / range |

Fast SE family block:

| 項目 | 必須度 | 備考 |
| --- | --- | --- |
| `alpha_ref_const_deg` | 必須 | 180 deg conventional を含む |
| `startup_ramp_mode` | 必須 | `none` / `manual` |
| `startup_ramp_values_deg[]` | 条件付き | manual 時のみ |
| `phase_encode_order_2d` | 2D 時必須 | linear / centric / reverse_centric |
| `Nslices` | 2D 時必須 | multi-slice 用 |
| `slice_thickness_mm` | 2D 時必須 | |
| `Nslice_slots_per_TR` | 2D 時必須 | scan time に影響 |
| `TE_nominal_ms` | 推奨 | nominal TE |

VFA-FSE family block:

| 項目 | 必須度 | 備考 |
| --- | --- | --- |
| `vfa_design_mode` | 必須 | `MANUAL` / `B2006` / `B2008` |
| `alpha_ref_train_deg[]` | MANUAL 時必須 | train 直接入力 |
| `phi_ref_train_deg[]` | 推奨 | refocusing phase |
| `alpha_min_deg` | B2008 時必須 | |
| `alpha_cent_deg` | B2008 時必須 | |
| `alpha_max_deg` | B2008 時必須 | |
| `n_cent` | B2008 時推奨 | |
| `n_min` | B2008 時推奨 | |
| `T1_design_ms`, `T2_design_ms` | B2006/B2008 時必須 | design tissue |
| `target_profile_mode` | B2006 時必須 | |
| `S_target`, `n_hold`, `p_pre`, `p_post`, `alpha_cap_deg` | B2006 時条件付き | target-envelope 系 |
| `view_order_mode_3d` | 3D 時必須 | `ky_mod` / `kr_mod` |
| `TE_equiv_target_ms` | 推奨 | target contrast |

### 5.3 Comparison

比較条件を定義する。

| 項目 | 役割 |
| --- | --- |
| `comparison_modes[]` | matched constraints の選択 |
| report preset | Report A / B / C の quick preset |
| tolerance panel | `epsilon_TE`, `epsilon_T`, `epsilon_SAR` など |
| reference side | `Run A` を基準にするか `Run B` を基準にするか |

### 5.4 Advanced

v0 では折りたたみでよい。

対象項目:

- RF selectivity
- RF durations
- crusher timing
- readout window
- autocalibration
- partial Fourier
- acceleration
- elliptical mask
- B1 sweep
- motion sweep

---

## 6. Right Pane: Inspector Tabs

Inspector は `Sequence`, `Timing / Contrast`, `Results`, `Comparison`, `Metadata`, `Log`
の 6 タブを持つ。

### 6.1 Sequence

実行前 preview と実行後の sequence audit を表示する。

表示内容:

- refocusing flip-angle train
- excitation / refocusing phase train
- event timeline
- derived `ESP`, `ESP1`, `ESP2`
- k-space ordering preview
- center-k mapping

このタブは「入力値がどういう sequence に展開されたか」を確認する場所であり、最初に見るタブとする。

### 6.2 Timing / Contrast

表示内容:

- `TE_nominal_ms`
- `TE_center_k_ms`
- `TE_equiv_Busse_ms`
- `ft_WH2006`
- `TE_contrast_WH_ms`
- `Tscan_s`
- matched-contrast 判定

要件:

- TE は 1 つの値にまとめず、定義ごとに明示的に分ける
- `FASTSE_CONST` では `TE_center-k` を主表示
- `VFA_FSE` では `TE_equiv_Busse` を主表示

### 6.3 Results

表示内容:

- echo signal per tissue
- FID signal per tissue
- center echo signal summary
- PSF 1D / PSF 2D
- `FWHM`
- `SLR`
- motion metric
- FID metric
- B1 robustness metric
- SNR / CNR / efficiency

タブ内の推奨サブセクション:

1. `Signal`
2. `Artifacts`
3. `Efficiency`

### 6.4 Comparison

表示内容:

- `parameter_table_A`
- `parameter_table_B`
- `matched_constraints_summary`
- `delta_TE_contrast`
- `delta_scan_time`
- `delta_SAR`
- `delta_voxel`
- `delta_coverage`
- `R_eta_SNR_time`
- `R_eta_SNR_vol`
- `R_eta_CNR_time`

このタブは最終的な比較レポート画面とし、表形式中心でよい。

### 6.5 Metadata

表示内容:

- input YAML / bundle metadata
- solver version
- schema version
- source paths
- warnings

### 6.6 Log

表示内容:

- validation messages
- compute log
- warning / error log

---

## 7. Center Pane: Animation Workspace

### 7.1 基本方針

Animation Workspace では、現行の `ScenePanel` と `PlaybackBar` を可能な限り維持する。

v0 の原則:

- scene 描画コードは大きく作り直さない
- generic 化は `ScenePanel` に渡す入力データの契約で吸収する
- sequence 固有の診断情報は Inspector 側に逃がす

### 7.2 表示対象

3D scene に表示する対象は、family 非依存の `trajectory entity` とする。

最低限必要な entity 種別:

- active trajectory
- compare trajectory
- active orbit
- compare orbit
- highlighted current vector
- optional auxiliary vector or marker

### 7.3 画面内コントロール

Playback 直上または scene 下に `Selection Strip` を置く。

項目:

| 項目 | 役割 |
| --- | --- |
| active slot | `A` / `B` |
| trajectory group | `reference`, `steady`, `echo-train`, `recovery` など |
| tissue selector | tissue 切替 |
| entity selector | spin / isochromat / representative trajectory |
| acquisition or train selector | train index / acquisition index |
| frame scrubber | 現在フレーム |
| overlay toggle | compare 表示 on/off |

重要な点として、generic viewer の canonical selector は `delta_f` 固定ではない。
Fast SE / VFA-FSE では `echo`, `train`, `tissue`, `entity` の方が前面に出る。

### 7.4 既存 bSSFP との互換

`BSSFP` family では selection strip の `entity selector` が実質 `delta_f / spin selector`
として振る舞ってよい。

---

## 8. 実行前に確認すべき項目

generic viewer では、Run 前に次を一目で確認できる必要がある。

### 8.1 sequence definition

- family
- dimensionality
- flip-angle train
- phase train
- ETL
- Nskip

### 8.2 timing feasibility

- user-entered `ESP`
- derived minimum `ESP`
- `ESP1`, `ESP2`
- feasibility warning

### 8.3 contrast definition

- nominal TE
- center-k TE
- Busse equivalent TE
- WH2006 `f_t`

### 8.4 efficiency / safety precheck

- scan time estimate
- SAR proxy
- RF power proxy
- voxel and coverage summary

### 8.5 k-space preview

- center-k echo index
- view order mode
- acquired views and train count

---

## 9. 実行後に確認すべき項目

### 9.1 signal evolution

- per-tissue echo envelope
- FID envelope
- center echo value

### 9.2 image-quality indicators

- PSF 1D / 2D
- `FWHM`
- `SLR`
- motion metric
- FID metric
- B1 robustness

### 9.3 efficiency

- `SNR_ROI`
- `CNR_ROI_pair`
- `SNR_eff_time`
- `SNR_eff_vol`
- `CNR_eff_time`

### 9.4 comparison outputs

- constraint satisfaction
- delta summary
- efficiency ratios

---

## 10. generic viewer 用データ契約

v0 では viewer 側に次の 3 種類の view-model が必要である。

### 10.1 `AnimationViewModel`

役割:

- `ScenePanel` と `PlaybackBar` に渡す family 非依存のアニメーション用データ

最低限必要な項目:

```text
run_label
sequence_family
trajectory_groups[]
current_group
frame_axis_s
entities[]
selection_defaults
```

各 entity が持つ情報:

```text
entity_id
entity_label
tissue_label
acquisition_or_train_index
logical_selector_value
vectors_xyz[frame, 3]
orbit_xyz[frame, 3] | None
metadata
```

### 10.2 `SequenceSummaryViewModel`

役割:

- Sequence タブと Timing / Contrast タブへ渡す preview / summary データ

最低限必要な項目:

```text
sequence_description
flip_train_deg[]
phase_train_deg[]
timing_table
te_summary
scan_time_summary
sar_summary
kspace_preview
warnings[]
```

### 10.3 `ComparisonSummaryViewModel`

役割:

- Comparison タブと Bottom Summary に渡す比較結果

最低限必要な項目:

```text
matched_constraints_summary
delta_metrics
efficiency_ratios
status_flags
report_metadata
```

---

## 11. 現行コードへのマッピング

### 11.1 維持するもの

- `ScenePanel`
- `PlaybackBar`
- PyVista fallback
- screenshot export の基礎

### 11.2 置き換えるもの

- `ConfigEditor`
  - family-aware な `ExperimentEditor` へ置換
- `DatasetViewModel`
  - `AnimationViewModel` 系へ置換または adapter 化
- `ComparisonController`
  - `delta_f` 固定選択から generic selection へ拡張
- `ProfilePanel`
  - profile 固定ではなく `ResultsInspector` 系へ分割

### 11.3 adapter 方針

最初は legacy bSSFP dataset から generic viewer 用 view-model へ変換する adapter を作る。
これにより、

- generic viewer 自体の UI を先に実装できる
- Fast SE / VFA-FSE 未実装でも BSSFP で動作確認できる
- 現行 viewer は当面そのまま残せる

---

## 12. v0 実装順

### Phase 1

- `ExperimentEditor` の枠組み
- `Sequence` / `Timing / Contrast` inspector
- `AnimationViewModel` adapter for BSSFP
- 既存 `ScenePanel` 接続

### Phase 2

- `Results` / `Comparison` inspector
- generic bottom summary
- comparison bundle 読み込み

### Phase 3

- Fast SE / VFA-FSE family block の実装
- preview generator の実装
- selector の generic 化

---

## 13. v0 受け入れ条件

### 13.1 UI

- `Run A` / `Run B` の family-aware editor が表示できる
- Sequence preview と Timing / Contrast summary が分離表示される
- existing 3D animation path が generic viewer から利用できる

### 13.2 情報設計

- Fast SE / VFA-FSE に必要な入力項目が不足なく整理されている
- run 前に `flip train`, `timing`, `TE`, `scan time`, `SAR`, `k-space ordering` を確認できる
- run 後に `signal`, `PSF`, `FID`, `efficiency`, `comparison ratios` を確認できる

### 13.3 互換

- legacy bSSFP viewer を壊さない
- generic viewer は BSSFP adapter で先に検証できる

---

## 14. 今後の判断ポイント

v0 以降で最初に詰めるべき論点は次の 3 つである。

1. generic selection の canonical 軸を何にするか
2. `ScenePanel` が受け取る generic entity contract をどこまで抽象化するか
3. `ProfilePanel` を generic `ResultsInspector` にどう分割するか

この 3 点が固まれば、Fast SE / VFA-FSE の family 実装と viewer 実装を並行して進めやすくなる。
