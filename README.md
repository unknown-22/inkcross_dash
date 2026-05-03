# Inkcross Dashboard

E-ink 端末向けのダッシュボード画像を生成・配信する FastAPI サーバです。

端末は `/dashboard.bmp` にアクセスするだけで、天気・今日の予定・未完了 ToDo をまとめた 480x800 の 4 階調グレースケール BMP を取得できます。

![ダッシュボード表示例](./image.png)

## Features

- 480x800 縦画面の E-ink 端末向けダッシュボード生成
- Open-Meteo API による東京周辺の天気予報表示
- `data/calendar.json` から今日の予定を読み込み
- `data/todo.json` から未完了 ToDo を読み込み
- Playwright で HTML をレンダリングし、Pillow で 4 階調 BMP に変換
- 端末側で扱いやすい固定 URL の画像配信

詳細な仕様は [SPEC.md](./SPEC.md) を参照してください。

## Requirements

- Python 3.13
- uv
- Playwright Chromium

依存パッケージは `pyproject.toml` と `uv.lock` で管理しています。

## Setup

```bash
uv sync
uv run playwright install chromium
```

## Run

```bash
uv run python main.py
```

デフォルトでは `0.0.0.0:8000` で起動します。

## API

### `GET /dashboard.bmp`

ダッシュボード画像を BMP 形式で返します。

- `Content-Type`: `image/bmp`
- サイズ: 480x800
- 色数: 4 階調グレースケール
- キャッシュ: `Cache-Control: no-store`

例:

```bash
curl -o dashboard.bmp http://localhost:8000/dashboard.bmp
```

### `GET /health`

ヘルスチェック用エンドポイントです。

```json
{"status": "ok"}
```

### `GET /docs`

FastAPI が自動生成する Swagger UI です。ブラウザで開くと、利用可能な API の一覧とレスポンス仕様を確認できます。

```text
http://localhost:8000/docs
```

### `GET /openapi.json`

FastAPI が自動生成する OpenAPI スキーマです。API クライアント生成や外部ツール連携に利用できます。

```text
http://localhost:8000/openapi.json
```

## Data Files

### `data/calendar.json`

今日の予定として表示するカレンダー項目を定義します。サーバ側で実行日の予定だけに絞り込み、開始時刻順に表示します。

```json
[
  {
    "title": "朝会",
    "start": "2026-05-03T09:30:00",
    "end": "2026-05-03T10:00:00",
    "location": "オンライン"
  }
]
```

### `data/todo.json`

未完了の ToDo を表示します。`done: false` の項目だけが対象です。

```json
[
  {
    "title": "請求書を送る",
    "done": false,
    "due": "2026-05-03"
  },
  {
    "title": "牛乳を買う",
    "done": false,
    "due": null
  }
]
```

期限が今日以前の ToDo は画面上で強調表示されます。

## Development

テストと静的解析は `uv run` 経由で実行します。

```bash
uv run pytest tests/
uv run ruff check
uv run ty check
uv run pyright
```

特定のテストだけを実行する例:

```bash
uv run pytest tests/test_renderer.py
```

## Project Structure

```text
.
├── app/
│   ├── dashboard.py      # データ収集と DashboardData 構築
│   ├── renderer.py       # HTML レンダリングと BMP 生成
│   ├── quantize.py       # 4 階調量子化と 4bit BMP エンコード
│   ├── weather.py        # Open-Meteo API クライアント
│   ├── calendar_loader.py
│   ├── todo_loader.py
│   └── models.py         # Pydantic モデル
├── data/
│   ├── calendar.json
│   └── todo.json
├── templates/
│   └── dashboard.html
├── tests/
├── main.py
├── SPEC.md
└── README.md
```
