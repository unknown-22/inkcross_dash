# instructions

**日本語で返答してください**

## プロジェクト概要

E-ink端末用ダッシュボードサーバ 

詳細な仕様は [SPEC.md](./SPEC.md) を参照してください。

## 主要技術スタック・コーディング規約

- 言語: Python 3.13
- フレームワーク: FastAPI

**プロジェクトルール**

- python 3.13のモダンな機能を活用する
- pydanticを利用し、型ヒントも積極的に使用する
- 適切な単位でモジュール化・クラス化を行う
- ロジック部分はクラス化・関数化してテスト可能にする
- ruff, ty, pyright を利用して静的解析を行う
  - ruff: コードスタイル、不要なimport、未使用変数など
  - ty: 型チェック
  - pyright: 型チェックの補完
- linterや型チェックで関数・引数ミスが出たら `inspect` モジュールで関数シグネチャを確認するワンライナーを都度作成し、調査と修正を繰り返す

## 開発環境とコマンド

uv run を利用してコマンドを実行します。

### 基本コマンド
```bash
# 実行
uv run python main.py

# 全テスト実行
uv run pytest tests/

# 特定のテストモジュール実行例
uv run pytest tests/test_module.py
```

### リンターとフォーマット
```bash
# Ruff実行
uv run ruff check
# Ruff実行と自動修正
uv run ruff check <file_name> --fix

# 型チェック(ty)
uv run ty check
uv run ty check <file_name>

# 型チェック(pyright)
uv run pyright
uv run pyright <file_name>
```

### 依存環境管理

uvを利用します

```bash
# 依存関係追加
uv add <package>
```
