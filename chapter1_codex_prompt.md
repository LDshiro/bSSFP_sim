# 第1章用 Codex 指示文

あなたは、ローカルの VS Code + Codex 環境で `bloch-ssfp-visualizer` プロジェクトの**第1章**を実装する担当です。

## 第1章の目標
今後の計算機能と可視化機能を安全に積み上げるために、次を満たす最小骨格を作ってください。

- 空の GUI が起動する
- 設定モデルとサンプル設定がある
- lint / type / test / pre-commit が通る
- 将来 `core`, `io`, `gui`, `viz`, `workflows` を拡張できる構造になっている

## 範囲
### 実装するもの
1. `src` レイアウトの Python パッケージ
2. `bssfpviz` という console script
3. PySide6 / Qt Widgets ベースの最小 GUI
4. 最小設定 dataclass と YAML サンプル
5. Ruff / mypy / pytest / pre-commit の設定
6. README / docs/chapters/chapter1.md の更新

### 実装しないもの
- Bloch solver 本体
- periodic steady-state solver
- HDF5 保存本体
- PyVista 埋め込み
- pyqtgraph プロット
- アニメーション
- 最適化機能

## 必須技術
- Python 3.11+
- PySide6 / Qt Widgets
- NumPy, SciPy, PyYAML, h5py は依存関係に含める
- pyvista, pyvistaqt, pyqtgraph は将来用の依存関係として含める
- Ruff, mypy, pytest, pre-commit を入れる

## 作るべきディレクトリ構成
```text
bloch-ssfp-visualizer/
  pyproject.toml
  README.md
  AGENTS.md
  WORKFLOW.md
  .pre-commit-config.yaml
  .gitignore
  src/
    bssfpviz/
      __init__.py
      app/
        __init__.py
        main.py
      core/
        __init__.py
      io/
        __init__.py
      gui/
        __init__.py
        main_window.py
      models/
        __init__.py
        config.py
      viz/
        __init__.py
      workflows/
        __init__.py
  tests/
    unit/
      test_imports.py
      test_config.py
    integration/
      test_app_boot.py
  examples/
    configs/
      minimal.yaml
  data/
    generated/
      .gitkeep
  docs/
    chapters/
      chapter1.md
  scripts/
      .gitkeep
```

## GUI の要件
- `bssfpviz` で起動できること
- `python -m bssfpviz.app.main` でも起動できること
- `QMainWindow` ベースであること
- ウィンドウタイトルは `Bloch / bSSFP Visualizer - Chapter 1` とすること
- 中央に `Chapter 1 skeleton` と表示するプレースホルダを置くこと
- `main.py` と `main_window.py` を分離すること
- 将来 panel や viewer を追加しやすいようにすること

## 設定モデルの要件
`models/config.py` に最低限次を作ること。
- `SequenceConfig`
- `PhysicsConfig`
- `AppConfig`
- `ProjectConfig`（または同等のルート設定）

また、`examples/configs/minimal.yaml` を用意し、最小ロード関数を作ること。YAML 読み込みは単純でよい。

## テストの要件
### unit
- 主要モジュールが import できる
- dataclass が生成できる
- minimal.yaml がロードできる

### integration
- `QApplication` と `MainWindow` が headless に近い形で起動できる
- テストは長時間ブロックしない

## 開発ツールの要件
- `ruff check .` が通る
- `ruff format --check .` が通る
- `mypy src` が通る
- `pytest` が通る
- `pre-commit` で上記を呼べる構成にする

## 実装の制約
- 過剰設計しない
- 章の範囲外の本実装を入れない
- 型注釈を付ける
- 公開関数に簡潔な docstring を付ける
- GUI と計算ロジックを混ぜない
- まずは最小差分で通す

## 作業手順の希望
1. 必要ファイルを作る
2. 最小実装を入れる
3. テストを書く / 整える
4. lint / type / test を実行する
5. README と docs を更新する

## Codex の出力形式
最終出力では次を必ず含めてください。

1. 変更ファイル一覧
2. 各ファイルの役割の短い説明
3. 実行したコマンド一覧
4. コマンド結果の要約
5. まだ未実装で次章へ送る項目

## 完了条件
以下を満たしたら第1章完了です。
- 空 GUI が起動する
- lint / type / test が通る
- 第2章へ自然に進める構造になっている
