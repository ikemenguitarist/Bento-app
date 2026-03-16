# Bento App

現在の実行系は Django です。このリポジトリでは `manage.py` を入口として扱います。

## 開発環境

1. 仮想環境を有効化します。
2. 依存をインストールします。

```powershell
venv\Scripts\pip.exe install -r requirements.txt
```

3. マイグレーションを適用します。

```powershell
venv\Scripts\python.exe manage.py migrate
```

4. 開発サーバーを起動します。

```powershell
venv\Scripts\python.exe manage.py runserver
```

## 主な画面

- `/`
  - 運営ハブ
- `/orders/dashboard/`
  - 当日ダッシュボード
- `/orders/delivery/`
  - 配送リスト
- `/orders/history/`
  - 注文履歴
- `/orders/companies/`
  - 企業・部署一覧
- `/orders/qr/`
  - QR 一覧
- `/admin/`
  - Django admin

## 補足

- 旧 Flask 実装は削除済みです。
- 現行DBは `db.sqlite3` です。
- 開発ルールは `codex-rules.md` を参照してください。
