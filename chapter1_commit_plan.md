# 第1章の推奨コミット分割

## コミット1
**chore: initialize project skeleton and tooling**

内容:
- `pyproject.toml`
- `.gitignore`
- `.pre-commit-config.yaml`
- `src/` レイアウト
- 空のパッケージ雛形

## コミット2
**feat: add minimal Qt main window and app entrypoint**

内容:
- `app/main.py`
- `gui/main_window.py`
- console script
- 最小 GUI 起動

## コミット3
**feat: add minimal config models and sample yaml**

内容:
- `models/config.py`
- `examples/configs/minimal.yaml`
- YAML ロードの最小支援

## コミット4
**test: add chapter1 unit and integration tests**

内容:
- import test
- config test
- app boot test

## コミット5
**docs: update readme and chapter1 notes**

内容:
- `README.md`
- `docs/chapters/chapter1.md`
- 必要なら `AGENTS.md`, `WORKFLOW.md` の軽微修正

## まとめ
1コミットに詰め込まず、上の 4〜5 分割で進めるとレビューしやすいです。
