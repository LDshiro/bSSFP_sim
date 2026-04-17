# 第1章: プロジェクト骨格と開発環境の実装

## 章の目的
この章の目的は、以降の計算機能と可視化機能を安全に積み上げるための**最小だが壊れにくい骨格**を作ることです。

この章では、まだ Bloch 方程式の本計算や HDF5 保存、3D アニメーション本体には入りません。代わりに、次の 4 点を満たす状態を作ります。

1. デスクトップ GUI が空の状態で起動する
2. 設定モデルと最小設定ファイルがある
3. lint / type / test / pre-commit が動く
4. 後の章で `core`, `io`, `viz`, `gui` を自然に拡張できる

## この章の完成物
- `src` レイアウトの Python パッケージ
- `bssfpviz` コマンド、または `python -m bssfpviz.app.main` で起動できる空 GUI
- 最小の dataclass 設定モデル
- 最小 YAML 設定ファイル
- Ruff / mypy / pytest / pre-commit が通る開発基盤
- 第1章の到達点を説明する `docs/chapters/chapter1.md`

## この章で扱う範囲
### やること
- プロジェクトのディレクトリ構成を作る
- 依存関係を定義する
- 最小 GUI を作る
- 最小設定モデルを作る
- unit test / integration test を追加する
- README と docs を現在の到達点に合わせて更新する

### やらないこと
- Bloch solver の本実装
- 厳密 propagator
- periodic steady-state solver
- HDF5 保存の本実装
- PyVista / pyvistaqt の埋め込み
- pyqtgraph による 2D プロット
- 最適化器や JAX 関連

## 推奨ディレクトリ構成
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

## 実装の要点
### 1. GUI は最小に留める
- `QMainWindow` ベース
- ウィンドウタイトルを明示する
- 中央にプレースホルダのラベルを置く
- 将来の panel 追加のためにウィンドウクラスを `main_window.py` に分離する

### 2. 設定モデルは軽く始める
次のような dataclass があれば十分です。
- `AppConfig`
- `SequenceConfig`
- `PhysicsConfig`
- `RootConfig` または `ProjectConfig`

後章で項目を増やす前提なので、最初は無理に詰め込みません。

### 3. headless テストを壊れにくくする
GUI の integration test は「起動できるか」だけ確認し、表示し続ける必要はありません。必要なら `QT_QPA_PLATFORM=offscreen` を使います。

### 4. 開発ツールは最初から入れる
- Ruff
- mypy
- pytest
- pre-commit

この章では品質基盤を先に通しておくことが重要です。

## 推奨する最小コマンド列
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .[dev]
pre-commit install
ruff check .
ruff format --check .
mypy src
pytest
bssfpviz
```

## 完了条件
以下を満たしたら第1章完了です。

1. `bssfpviz` で空 GUI が起動する
2. `ruff check .` が通る
3. `ruff format --check .` が通る
4. `mypy src` が通る
5. `pytest` が通る
6. README / AGENTS / WORKFLOW / chapter1.md が現在の実装と矛盾しない
7. 第2章でデータモデルと HDF5 保存に進める構成になっている

## この章のゴールの見方
この章は「動く最小アプリ」と「壊れにくい開発環境」を作る章です。機能の派手さではなく、次章以降で差分を安全に積めることを重視してください。
