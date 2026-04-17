# 第1章レビュー用チェックリスト

## A. 起動確認
- [ ] `bssfpviz` で GUI が起動する
- [ ] `python -m bssfpviz.app.main` でも GUI が起動する
- [ ] ウィンドウタイトルが想定どおり
- [ ] 中央にプレースホルダが表示される

## B. ディレクトリ構成
- [ ] `src/bssfpviz/app` がある
- [ ] `src/bssfpviz/gui` がある
- [ ] `src/bssfpviz/models` がある
- [ ] `src/bssfpviz/core`, `io`, `viz`, `workflows` が雛形としてある
- [ ] `tests/unit` と `tests/integration` が分かれている
- [ ] `examples/configs/minimal.yaml` がある
- [ ] `docs/chapters/chapter1.md` がある

## C. 設定モデル
- [ ] dataclass で最小設定が表現されている
- [ ] YAML から最小設定をロードできる
- [ ] モデル名とフィールド名が後章で拡張しやすい

## D. 開発基盤
- [ ] `pyproject.toml` に依存関係が定義されている
- [ ] console script が定義されている
- [ ] `.pre-commit-config.yaml` がある
- [ ] `.gitignore` が適切

## E. テスト
- [ ] `ruff check .` が通る
- [ ] `ruff format --check .` が通る
- [ ] `mypy src` が通る
- [ ] `pytest` が通る
- [ ] GUI の integration test が headless に近い形で通る

## F. ドキュメント
- [ ] README が現在の到達点と一致している
- [ ] chapter1.md に起動方法とテスト方法がある
- [ ] AGENTS.md / WORKFLOW.md と実装が矛盾していない

## G. 次章へ渡す条件
- [ ] 第2章で HDF5 スキーマや round-trip を実装しやすい構造になっている
- [ ] `models` と `io` が独立している
- [ ] GUI 起動コードが計算コードに依存していない
