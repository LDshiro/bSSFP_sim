# AGENTS.md

## 目的
このリポジトリは、bSSFP / Bloch 方程式の挙動を観察するためのローカル GUI ツールを、章ごとに段階的に実装するためのものです。  
当面の主目的は、次の二系統を安全に統合できる骨格を育てることです。

1. 計算コア
   - Bloch 方程式の時間積分
   - 周期境界条件と厳密 propagator による steady-state 解法
   - Δf sweep と profile 計算
2. 観察系
   - 3D ベクトル表示
   - profile 表示
   - 保存済みデータの読み込みと再生

## 開発方針
- 章単位で進める
- 各章では「その章で必要な最小機能のみ」を作る
- 将来の拡張性は意識するが、先回りして過剰設計しない
- まずは観察対象の系を安定に可視化することを優先し、最適化器は後段に置く

## 採用技術
- Python 3.11+
- GUI: PySide6 / Qt Widgets
- 3D 表示: PyVista + pyvistaqt
- 2D 表示 / 軽量 UI 補助: pyqtgraph
- 数値計算: NumPy, SciPy
- データ保存: HDF5 (h5py)
- 設定: YAML
- 品質管理: ruff, mypy, pytest, pre-commit

## ディレクトリの責務
- `src/bssfpviz/app/`
  - エントリポイント
  - アプリ起動処理
- `src/bssfpviz/gui/`
  - Qt Widgets ベースの GUI 部品
- `src/bssfpviz/viz/`
  - PyVista / pyqtgraph を使う表示ロジック
- `src/bssfpviz/core/`
  - Bloch solver、steady-state solver、signal/profile 計算
- `src/bssfpviz/io/`
  - HDF5 / YAML の読み書き
- `src/bssfpviz/models/`
  - dataclass や設定モデル
- `src/bssfpviz/workflows/`
  - 計算実行や GUI から呼ぶ高レベル処理
- `tests/`
  - unit / integration に分ける
- `examples/configs/`
  - 手で動かせる最小設定
- `docs/chapters/`
  - 各章の到達点メモ

## 実装ルール
- 章の範囲外の機能は作り込みすぎない
- すべての公開関数・メソッドに型注釈を付ける
- GUI ロジックと計算ロジックを分離する
- 数値配列は可能な範囲で shape を意識した命名にする
- 後で JAX へ移植する可能性を妨げる密結合を避ける
- 保存形式は後方互換性を意識し、将来的に version を付ける

## テスト方針
- 各章で最小限の unit test と integration test を追加する
- GUI テストは「headless 環境でも壊れにくい最小確認」に留める
- 数値テストは最初は小さく始め、後章で精度保証を強める
- lint / type / test を pre-commit に通す

## Codex への期待
Codex は、現在の章の範囲だけを実装する。  
勝手に先の章の機能を入れすぎないこと。  
変更したファイルの役割、実行したコマンド、未実装事項を明記すること。
